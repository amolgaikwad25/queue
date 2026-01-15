from django.urls import path
from . import views

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('<int:service_id>/', views.service_detail, name='service_detail'),
    path('<int:service_id>/join/', views.join_queue, name='join_queue'),
]