from django.urls import path
from . import views

urlpatterns = [
    path('', views.voice_interface, name='voice_interface'),
    path('process/', views.process_voice, name='process_voice'),
    path('process-text/', views.process_voice_text, name='process_voice_text'),
    path('info/', views.get_queue_info, name='get_queue_info'),
]