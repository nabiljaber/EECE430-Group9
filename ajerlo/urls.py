# ajerlo/urls.py
from django.contrib import admin
from django.urls import path, include
from rentals.views import home

urlpatterns = [
    path("admin/", admin.site.urls),

    # Home page
    path("", home, name="home"),

    # Rentals app
    path("rentals/", include("rentals.urls")),

    # Accounts app (signup, login, account_overview, etc.)
    path("accounts/", include("accounts.urls")),
]
