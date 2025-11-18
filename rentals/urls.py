# rentals/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public
    path("", views.car_list, name="car_list"),
    path("<int:pk>/", views.car_detail, name="car_detail"),
    path("<int:pk>/book/", views.create_booking, name="create_booking"),
    path("<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("favorites/", views.favorites_list, name="favorites_list"),

    # Legacy (kept; guarded in the view)
    path("add/", views.add_car, name="add_car"),

    # Dealer
    path("dealer/apply/", views.dealer_apply, name="dealer_apply"),
    path("dealer/dashboard/", views.dealer_dashboard, name="dealer_dashboard"),
    path("dealer/cars/add/", views.dealer_add_car, name="dealer_add_car"),
    path("dealer/cars/<int:pk>/price/", views.dealer_update_price, name="dealer_update_price"),
    path("dealer/cars/<int:pk>/edit/", views.dealer_edit_car, name="dealer_edit_car"),
    path("dealer/cars/<int:pk>/delete/", views.dealer_delete_car, name="dealer_delete_car"),
    path("dealer/cars/<int:pk>/bookings/", views.dealer_car_bookings, name="dealer_car_bookings"),
    path("dealer/bookings/<int:pk>/status/", views.dealer_update_booking_status, name="dealer_update_booking_status"),
]
