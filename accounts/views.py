from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from queue_system.models import Queue
from services.models import Service
from datetime import datetime, timedelta
from .forms import CustomUserCreationForm

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Check for admin security code
            admin_code = form.cleaned_data.get('admin_code')
            if admin_code == '123':
                user.is_staff = True
                user.is_superuser = True
                user.save()
                messages.success(request, f'Admin account created for {user.username}! Your UQID is {user.uqid}')
            else:
                messages.success(request, f'Account created for {user.username}! Your UQID is {user.uqid}')

            login(request, user)
            return redirect('home')
        else:
            print("Form errors:", form.errors)  # Debug print
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'accounts/login.html')

@login_required
def user_dashboard(request):
    user_queues = Queue.objects.filter(user=request.user).order_by('-joined_at')
    active_queue = user_queues.filter(status__in=['waiting', 'serving']).first()

    # Calculate estimated time remaining
    estimated_time = None
    position = None

    if active_queue:
        # Count people ahead in queue
        ahead_count = Queue.objects.filter(
            service=active_queue.service,
            status='waiting',
            token_number__lt=active_queue.token_number
        ).count()

        position = ahead_count + 1

        # Estimate 5 minutes per person
        estimated_time = ahead_count * 5

    context = {
        'user_queues': user_queues,
        'active_queue': active_queue,
        'position': position,
        'estimated_time': estimated_time,
    }

    return render(request, 'accounts/dashboard.html', context)

def user_logout(request):
    logout(request)
    return redirect('home')

def profile(request):
    from django.contrib.auth.decorators import login_required
    from django.shortcuts import render

    @login_required
    def _profile(req):
        user = req.user
        total_queues = user.queue_set.count()
        completed_count = user.queue_set.filter(status='completed').count()
        active_count = user.queue_set.filter(status__in=['waiting', 'serving']).count()
        recent_queues = user.queue_set.select_related('service').order_by('-joined_at')[:10]

        context = {
            'user': user,
            'total_queues': total_queues,
            'completed_count': completed_count,
            'active_count': active_count,
            'recent_queues': recent_queues,
        }
        return render(req, 'accounts/profile.html', context)

    return _profile(request)
