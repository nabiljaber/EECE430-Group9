# ajerlo/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Home page
    path("", views.home, name="home"),

    # Rentals app
    path("rentals/", include("rentals.urls")),

    # Accounts app (signup, login, account_overview, etc.)
    path("accounts/", include("accounts.urls")),
]

if settings.DEBUG:
    # Serve media files in DEBUG
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # 🔥 Serve static files (CSS, images) from STATIC_ROOT -> /static/
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
