from django.contrib import admin

# Register your models here.
<<<<<<< HEAD
from django.contrib import admin
from .models import Dealer, Car

@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "active")
    list_filter = ("active",)
    search_fields = ("name", "user__username", "user__email")

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("title", "price_per_day", "dealer")
    list_filter = ("dealer",)
    search_fields = ("title", "dealer__name")
=======
>>>>>>> 75f6ec464013ed4df1d1158a123edad786a0c61a
