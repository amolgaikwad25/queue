from django.urls import path
from . import views

urlpatterns = [
    path('status/<int:queue_id>/', views.queue_status, name='queue_status'),
    path('my-queues/', views.my_queues, name='my_queues'),
    path('api/<int:service_id>/', views.queue_api, name='queue_api'),
    path('eta/<int:queue_id>/', views.queue_eta, name='queue_eta'),
    path('cancel/<int:queue_id>/', views.cancel_own_queue, name='cancel_own_queue'),
]