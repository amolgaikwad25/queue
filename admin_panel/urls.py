from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('service/<int:service_id>/', views.service_queues, name='service_queues'),
    path('service/<int:service_id>/call-next/', views.call_next, name='call_next'),
    path('service/<int:service_id>/pause/', views.pause_service_view, name='pause_service'),
    path('service/<int:service_id>/resume/', views.resume_service_view, name='resume_service'),
    path('queue/<int:queue_id>/complete/', views.complete_queue, name='complete_queue'),
    path('queue/<int:queue_id>/skip/', views.skip_queue, name='skip_queue'),
    path('queue/<int:queue_id>/cancel/', views.cancel_queue, name='cancel_queue'),
    path('queue/<int:queue_id>/send-sms/', views.send_token_sms_view, name='send_token_sms'),
]