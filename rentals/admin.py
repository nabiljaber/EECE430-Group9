# rentals/admin.py
from django.contrib import admin
from .models import Dealer, Car, CarImage, Booking


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "active")
    list_filter = ("active",)
    search_fields = ("name", "user__username", "user__email")


class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 0


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("title", "price_per_day", "dealer", "available", "car_type", "year")
    list_filter = ("dealer", "available", "car_type", "transmission", "year")
    search_fields = ("title", "dealer__name", "make", "model")
    inlines = [CarImageInline]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("car", "user", "start_date", "end_date", "status", "total_price", "currency")
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("car__title", "user__username", "user__email")
