from django.urls import path
from .views import SignUpView, logout_then_home, account_dashboard

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("logout/", logout_then_home, name="logout"),  # override default logout
    path("dashboard/", account_dashboard, name="account_dashboard"),
]
