from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Queue
from services.models import Service
from services.utils import get_queue_eta
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

@login_required
def queue_status(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, user=request.user)
    return render(request, 'queue_system/queue_status.html', {'queue': queue})

@login_required
def my_queues(request):
    queues = Queue.objects.filter(user=request.user).order_by('-joined_at')
    return render(request, 'queue_system/my_queues.html', {'queues': queues})

def queue_api(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    queues = Queue.objects.filter(service=service, status__in=['waiting', 'serving']).order_by('token_number')

    data = {
        'service': service.name,
        'queues': [
            {
                'token': q.token_number,
                'status': q.status,
                'user_uqid': q.user.uqid if q.status == 'serving' else None
            } for q in queues
        ]
    }
    return JsonResponse(data)


@login_required
def queue_eta(request, queue_id):
    """Return ETA and status info for a user's queue entry.

    Response JSON:
    - queue_id, token_number, status, tokens_ahead, eta_minutes, current_serving
    """
    queue = get_object_or_404(Queue, pk=queue_id)
    # Only owner or staff can access ETA for this queue
    if request.user != queue.user and not request.user.is_staff:
        return JsonResponse({'error': 'forbidden'}, status=403)

    info = get_queue_eta(queue_id)
    return JsonResponse(info)


@login_required
def cancel_own_queue(request, queue_id):
    """Allow a user to cancel their own waiting token.

    Only tokens with status 'waiting' can be cancelled by the user.
    """
    queue = get_object_or_404(Queue, pk=queue_id, user=request.user)
    if queue.status != 'waiting':
        return JsonResponse({'error': 'cannot_cancel'}, status=400)

    from services.utils import cancel_token
    cancelled, _ = cancel_token(queue.id)
    return JsonResponse({'status': 'cancelled', 'queue_id': cancelled.id})
