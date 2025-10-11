from django.urls import path
from . import views

urlpatterns = [
    path('', views.car_list, name='car_list'),
    path('<int:pk>/', views.car_detail, name='car_detail'),
    path('<int:pk>/book/', views.create_booking, name='create_booking'),
    path('add/', views.add_car, name='add_car'),
]
