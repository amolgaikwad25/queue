from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Service
from queue_system.models import Queue
from .utils import issue_token

@login_required
def service_list(request):
    services = Service.objects.all()
    return render(request, 'services/service_list.html', {'services': services})

@login_required
def service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    return render(request, 'services/service_detail.html', {'service': service})

@login_required
def join_queue(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    # Check if user already has an active queue for this service
    existing_queue = Queue.objects.filter(
        user=request.user,
        service=service,
        status__in=['waiting', 'serving']
    ).first()

    if existing_queue:
        return render(request, 'services/already_in_queue.html', {'queue': existing_queue})

    # Issue token using a safe utility to prevent races and skipped/duplicate numbers
    queue = issue_token(request.user, service)

    return redirect('queue_status', queue_id=queue.id)
