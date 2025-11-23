from django.urls import path
from . import views

urlpatterns = [
    path("cars/", views.car_list, name="api_cars"),
    path("cars/<int:pk>/", views.car_detail, name="api_car_detail"),
    path("bookings/", views.create_booking, name="api_booking_create"),
    path("bookings/mine/", views.my_bookings, name="api_bookings_mine"),
    path("dealer/apply/", views.dealer_apply, name="api_dealer_apply"),
    path("favorites/", views.favorites_list, name="api_favorites"),
    path("favorites/toggle/", views.toggle_favorite, name="api_favorites_toggle"),
    path("dealer/dashboard/", views.dealer_dashboard, name="api_dealer_dashboard"),
    path("dealer/cars/", views.dealer_cars, name="api_dealer_cars"),
    path("dealer/cars/<int:pk>/", views.dealer_car_update, name="api_dealer_car_update"),
    path("dealer/cars/<int:pk>/price/", views.dealer_car_price, name="api_dealer_car_price"),
    path("dealer/cars/<int:pk>/bookings/", views.dealer_car_bookings, name="api_dealer_car_bookings"),
    path("dealer/bookings/<int:booking_id>/status/", views.dealer_booking_status, name="api_dealer_booking_status"),
]
