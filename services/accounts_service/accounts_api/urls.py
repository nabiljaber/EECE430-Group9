from django.urls import path
from . import views

urlpatterns = [
    path("auth/login/", views.login_view, name="api_login"),
    path("auth/signup/", views.signup_view, name="api_signup"),
    path("auth/me/", views.me_view, name="api_me"),
    path("auth/logout/", views.logout_view, name="api_logout"),
    path("auth/refresh/", views.refresh_view, name="api_refresh"),
    path("auth/password-reset/", views.password_reset_request, name="api_password_reset"),
    path("auth/password-reset/confirm/", views.password_reset_confirm, name="api_password_reset_confirm"),
    path("users/me/", views.user_update, name="api_user_update"),
]
