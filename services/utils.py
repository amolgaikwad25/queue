from django.db import transaction
from django.utils import timezone
from django.db.models import Max
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from .models import Service
from queue_system.models import Queue
from django.contrib.auth import get_user_model

User = get_user_model()


def issue_token(user, service):
    """Issue the next sequential token for a service safely using a DB lock.

    Returns the created Queue instance.
    """
    # Try to create a token in a transaction, using the maximum of stored last_token_number
    # and any existing token_number in the DB to avoid duplicates when inconsistencies exist.
    with transaction.atomic():
        svc = Service.objects.select_for_update().get(pk=service.pk)

        # Get current max token for the service from DB
        agg = Queue.objects.filter(service=svc).aggregate(max_token=Max('token_number'))
        max_token = agg.get('max_token') or 0

        base = max(svc.last_token_number or 0, max_token)
        next_token = base + 1

        # Update the service last_token_number to the new value
        svc.last_token_number = next_token
        svc.save(update_fields=["last_token_number"])

        # Create the queue entry. Wrap in try/except to handle rare race that still
        # results in an IntegrityError, in which case retry once.
        try:
            queue = Queue.objects.create(
                user=user,
                service=service,
                token_number=next_token,
                status='waiting'
            )
        except (IntegrityError, ValidationError):
            # Another process inserted the same token_number concurrently. Retry once.
            # Note: This should be exceedingly rare because we locked Service, but
            # extra safety ensures we do not raise a ValidationError to the user.
            transaction.set_rollback(False)
            # Recompute next token and try again
            svc = Service.objects.select_for_update().get(pk=service.pk)
            agg = Queue.objects.filter(service=svc).aggregate(max_token=Max('token_number'))
            max_token = agg.get('max_token') or 0
            next_token = max(svc.last_token_number or 0, max_token) + 1
            svc.last_token_number = next_token
            svc.save(update_fields=["last_token_number"])
            # second attempt - if this also fails it will raise to caller
            queue = Queue.objects.create(
                user=user,
                service=service,
                token_number=next_token,
                status='waiting'
            )

    return queue


def complete_current_and_serve_next(service):
    """Complete the currently serving token (if any) and serve the next waiting token.

    Ensures only one token per service is in 'serving' state by using transactions and
    row-level locks on the Queue rows and Service row.
    Returns a tuple (completed_queue, next_queue) where either may be None.
    """
    with transaction.atomic():
        svc = Service.objects.select_for_update().get(pk=service.pk)

        # Close out the currently serving token (if any)
        current = (
            Queue.objects.select_for_update()
            .filter(service=svc, status='serving')
            .order_by('token_number')
            .first()
        )

        completed = None
        if current:
            current.status = 'completed'
            now = timezone.now()
            current.service_end_time = now
            current.completed_at = now
            current.save()
            completed = current

        # If the service is paused, do not assign a new serving token
        if svc.paused:
            return (completed, None)

        # Pick the next waiting token in order. Consider priority_level first (higher first),
        # then ascending token_number to keep FIFO among same priority.
        next_q = (
            Queue.objects.select_for_update()
            .filter(service=svc, status='waiting')
            .order_by('-priority_level', 'token_number')
            .first()
        )

        if next_q:
            now = timezone.now()
            next_q.status = 'serving'
            next_q.service_start_time = now
            next_q.served_at = now
            next_q.save()

        return (completed, next_q)


def serve_next_without_completing(service):
    """Mark the next waiting token as serving without changing current serving token.

    Use-case: when no current serving token exists but admin requests to serve next.
    """
    with transaction.atomic():
        svc = Service.objects.select_for_update().get(pk=service.pk)
        if svc.paused:
            return None

        # Ensure no other token is serving
        existing = Queue.objects.filter(service=svc, status='serving').exists()
        if existing:
            return None

        next_q = (
            Queue.objects.select_for_update()
            .filter(service=svc, status='waiting')
            .order_by('-priority_level', 'token_number')
            .first()
        )

        if next_q:
            now = timezone.now()
            next_q.status = 'serving'
            next_q.service_start_time = now
            next_q.served_at = now
            next_q.save()
        return next_q


def skip_token(queue_id, admin_user=None, reason=None):
    """Skip (cancel) a token and if it was serving, serve the next one.

    Returns (skipped_queue, next_served_queue)
    """
    with transaction.atomic():
        q = Queue.objects.select_for_update().get(pk=queue_id)
        was_serving = q.status == 'serving'
        q.status = 'cancelled'
        now = timezone.now()
        q.service_end_time = now
        q.completed_at = now
        if reason:
            q.skip_reason = reason
        q.save()

        # Log admin action if provided (import locally to avoid circular imports)
        if admin_user:
            from admin_panel.models import AuditLog
            AuditLog.objects.create(
                user=admin_user,
                service=q.service,
                action='skip' if reason else 'cancel',
                target_queue=q,
                reason=reason
            )

        next_q = None
        if was_serving:
            # serve next if any
            _, next_q = complete_current_and_serve_next(q.service)

        return (q, next_q)


def cancel_token(queue_id, admin_user=None, reason=None):
    """Cancel a token (user or admin). If it was serving, serve next.

    Returns (cancelled_queue, next_served_queue)
    """
    return skip_token(queue_id, admin_user=admin_user, reason=reason)


def reorder_queue(service, ordered_queue_ids, admin_user=None, reason=None):
    """Reorder tokens for a service according to ordered_queue_ids.

    This operation should only be used when the service is paused.
    It will reassign token_number sequentially following the provided order.
    """
    with transaction.atomic():
        svc = Service.objects.select_for_update().get(pk=service.pk)
        if not svc.paused:
            raise ValueError('Service must be paused to reorder tokens')

        # Fetch current waiting queues for the service
        queues = list(Queue.objects.select_for_update().filter(service=svc, status='waiting'))
        id_to_q = {q.id: q for q in queues}

        # Validate provided ids
        if set(ordered_queue_ids) != set(id_to_q.keys()):
            raise ValueError('Ordered IDs must match existing waiting queue IDs')

        # Reassign token numbers based on new order
        # Keep starting token_number base as the minimum token in current waiting set
        base = min(q.token_number for q in queues) if queues else 1
        for idx, qid in enumerate(ordered_queue_ids):
            q = id_to_q[qid]
            q.token_number = base + idx
            q.save()

        # Log the reorder (import locally to avoid circular imports)
        if admin_user:
            from admin_panel.models import AuditLog
            AuditLog.objects.create(
                user=admin_user,
                service=svc,
                action='reorder',
                reason=reason
            )

        return True


def pause_service(service_id):
    svc = get_object_or_404(Service, pk=service_id)
    svc.paused = True
    svc.save(update_fields=['paused'])
    return svc


def resume_service(service_id):
    svc = get_object_or_404(Service, pk=service_id)
    svc.paused = False
    svc.save(update_fields=['paused'])
    return svc


def get_queue_eta(queue_id):
    """Return ETA information for a specific Queue entry.

    Returns dict: {
        'queue_id': int,
        'token_number': int,
        'status': str,
        'tokens_ahead': int,
        'eta_minutes': int,
        'current_serving': int|None,
    }
    """
    q = get_object_or_404(Queue, pk=queue_id)
    svc = q.service

    # Count waiting tokens with smaller token_number
    tokens_ahead = (
        Queue.objects.filter(service=svc, status='waiting', token_number__lt=q.token_number)
        .count()
    )

    # If there is a current serving token with token_number < q.token_number,
    # then that token contributes to waiting time as well.
    current_serving = (
        Queue.objects.filter(service=svc, status='serving').order_by('token_number').first()
    )

    if current_serving and current_serving.token_number < q.token_number:
        extra = 1
    else:
        extra = 0

    total_ahead = tokens_ahead + extra

    eta_minutes = total_ahead * (svc.avg_service_time or 5)

    return {
        'queue_id': q.pk,
        'token_number': q.token_number,
        'status': q.status,
        'tokens_ahead': total_ahead,
        'eta_minutes': eta_minutes,
        'current_serving': current_serving.token_number if current_serving else None,
    }
