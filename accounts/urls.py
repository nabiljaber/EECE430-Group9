# accounts/urls.py
from django.urls import path
from .views import SignUpView, account_overview, account_dashboard, login_view, logout_view

urlpatterns = [
    # Signup
    path('signup/', SignUpView.as_view(), name='signup'),

    # Account dashboard (bookings)
    path('dashboard/', account_dashboard, name='account_dashboard'),

    # Account overview (profile page)
    path('account/', account_overview, name='account_overview'),

    # Auth views
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Password reset/change could be added via accounts service
]
