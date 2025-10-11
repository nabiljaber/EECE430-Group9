from django.contrib import admin
from django.urls import path, include
from rentals.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('rentals/', include('rentals.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # login/logout
]
