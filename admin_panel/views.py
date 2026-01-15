from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from queue_system.models import Queue
from services.models import Service
from services.utils import (
    complete_current_and_serve_next,
    serve_next_without_completing,
    skip_token,
    cancel_token,
    pause_service,
    resume_service,
    reorder_queue,
)
from accounts.models import User
from django.utils import timezone
from django.shortcuts import HttpResponse
from django.views.decorators.http import require_POST
from .models import AuditLog
from django.views.decorators.csrf import csrf_protect
from notifications.sms_service import send_token_sms
from notifications.models import AdminSMSLog

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        admin_password = request.POST.get('admin_password')

        # First authenticate the user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if admin password is correct
            if admin_password == '123':
                # Check if user is staff/admin
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    return redirect('admin_dashboard')
                else:
                    messages.error(request, 'You do not have admin privileges.')
            else:
                messages.error(request, 'Invalid admin password.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'admin_panel/login.html')

@staff_member_required
def admin_dashboard(request):
    services = Service.objects.all()
    total_users = User.objects.count()
    total_queues = Queue.objects.count()
    active_queues = Queue.objects.filter(status__in=['waiting', 'serving']).count()
    completed_queues = Queue.objects.filter(status='completed').count()

    # Get recent queues
    recent_queues = Queue.objects.select_related('user', 'service').order_by('-joined_at')[:10]

    # Annotate services with queue counts
    for service in services:
        service.in_queue_count = service.queue_set.filter(status__in=['waiting', 'serving']).count()
        service.completed_count = service.queue_set.filter(status='completed').count()
        service.serving_count = service.queue_set.filter(status='serving').count()

    context = {
        'services': services,
        'total_users': total_users,
        'total_queues': total_queues,
        'active_queues': active_queues,
        'completed_queues': completed_queues,
        'recent_queues': recent_queues,
    }

    return render(request, 'admin_panel/dashboard.html', context)

@staff_member_required
def service_queues(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    queues = Queue.objects.filter(service=service, status__in=['waiting', 'serving']).order_by('token_number')
    return render(request, 'admin_panel/service_queues.html', {'service': service, 'queues': queues})


@staff_member_required
def skip_queue(request, queue_id):
    if request.method == 'POST':
        reason = request.POST.get('reason')
        skipped, next_q = skip_token(queue_id, admin_user=request.user, reason=reason)
        return redirect('service_queues', service_id=skipped.service.id)
    return HttpResponse(status=405)


@staff_member_required
def cancel_queue(request, queue_id):
    if request.method == 'POST':
        reason = request.POST.get('reason')
        cancelled, next_q = cancel_token(queue_id, admin_user=request.user, reason=reason)
        return redirect('service_queues', service_id=cancelled.service.id)
    return HttpResponse(status=405)


@staff_member_required
def call_next(request, service_id):
    if request.method == 'POST':
        service = get_object_or_404(Service, id=service_id)
        completed, next_q = complete_current_and_serve_next(service)
        # Log audit
        AuditLog.objects.create(user=request.user, service=service, action='serve_next')
        return redirect('service_queues', service_id=service_id)
    return HttpResponse(status=405)


@staff_member_required
def pause_service_view(request, service_id):
    if request.method == 'POST':
        svc = pause_service(service_id)
        AuditLog.objects.create(user=request.user, service=svc, action='pause')
        return redirect('service_queues', service_id=svc.id)
    return HttpResponse(status=405)


@staff_member_required
def resume_service_view(request, service_id):
    if request.method == 'POST':
        svc = resume_service(service_id)
        AuditLog.objects.create(user=request.user, service=svc, action='resume')
        return redirect('service_queues', service_id=svc.id)
    return HttpResponse(status=405)

@staff_member_required
@staff_member_required
def complete_queue(request, queue_id):
    if request.method == 'POST':
        queue = get_object_or_404(Queue, id=queue_id)
        # Use the utility to complete current and serve next only if this was serving
        if queue.status == 'serving':
            complete_current_and_serve_next(queue.service)
            AuditLog.objects.create(user=request.user, service=queue.service, action='complete', target_queue=queue)
        else:
            queue.status = 'completed'
            queue.service_end_time = timezone.now()
            queue.completed_at = timezone.now()
            queue.save()
            AuditLog.objects.create(user=request.user, service=queue.service, action='complete', target_queue=queue)

        return redirect('service_queues', service_id=queue.service.id)
    return HttpResponse(status=405)


@staff_member_required
def send_token_sms_view(request, queue_id):
    """Admin view: show form and send a manual SMS for a specific token.

    GET: render a small form showing token info and message box.
    POST: validate and call `send_token_sms` service, show success/failure.
    """
    queue = get_object_or_404(Queue, id=queue_id)
    user = getattr(queue, 'user', None)
    # Derive display phone (+91 prefixed if valid) without modifying user
    phone = (getattr(user, 'phone_number', None) or getattr(user, 'phone', None)) if user else None
    display_phone = f"+91{phone}" if phone and phone.isdigit() and len(phone) == 10 else ''

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        try:
            log = send_token_sms(queue, message, sent_by_admin_user=request.user)
            AuditLog.objects.create(user=request.user, service=queue.service, action='send_sms', target_queue=queue)
            messages.success(request, 'SMS queued for delivery (check SMS logs for status).')
            return redirect('service_queues', service_id=queue.service.id)
        except Exception as e:
            messages.error(request, f'Failed to send SMS: {e}')

    # Predefined templates
    templates = {
        'next': f"Your token #{queue.token_number} is next. Please be ready.",
        'serving': f"Now serving token #{queue.token_number}. Proceed to counter.",
        'delayed': f"Your token #{queue.token_number} is delayed. We will update soon.",
    }

    return render(request, 'admin_panel/send_sms.html', {
        'queue': queue,
        'user': user,
        'display_phone': display_phone,
        'templates': templates,
    })

