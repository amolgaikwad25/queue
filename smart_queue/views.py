from django.shortcuts import render
from services.models import Service
from queue_system.models import Queue

def home(request):
    # Get statistics for the dashboard
    services = Service.objects.all()
    total_queues = Queue.objects.count()
    active_queues = Queue.objects.filter(status__in=['waiting', 'serving']).count()
    total_services = services.count()

    context = {
        'services': services,
        'total_services': total_services,
        'total_queues': total_queues,
        'active_queues': active_queues,
    }

    return render(request, 'home.html', context)