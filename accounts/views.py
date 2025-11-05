# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import SignUpForm
from rentals.models import Booking

class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")

def logout_then_home(request):
    logout(request)
    return render(request, "registration/logged_out.html")

@login_required
def account_dashboard(request):
    bookings = (Booking.objects
                .select_related("car")
                .filter(user=request.user)
                .order_by("-created_at"))
    return render(request, "account/dashboard.html", {"bookings": bookings})
