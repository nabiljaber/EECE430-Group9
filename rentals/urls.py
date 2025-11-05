from django.urls import path
from . import views

urlpatterns = [
    path('', views.car_list, name='car_list'),
    path('<int:pk>/', views.car_detail, name='car_detail'),
    path('<int:pk>/book/', views.create_booking, name='create_booking'),
    path('add/', views.add_car, name='add_car'),
     path("dealer/dashboard/", views.dealer_dashboard, name="dealer_dashboard"),
    path("dealer/cars/add/", views.dealer_add_car, name="dealer_add_car"),
    path("dealer/cars/<int:pk>/price/", views.dealer_update_price, name="dealer_update_price"),
     path("dealer/apply/", views.dealer_apply, name="dealer_apply"),
]
