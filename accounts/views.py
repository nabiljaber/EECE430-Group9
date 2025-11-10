# accounts/views.py
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import SignUpForm
from rentals.models import Booking


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        """
        After creating the account, send the user to the login page
        and show a green success message (rendered in base.html).
        """
        response = super().form_valid(form)
        messages.success(self.request, "Account created successfully. You can now sign in.")
        return response


def logout_then_home(request):
    """
    Sign out and send the user to the Home page with a green notice.
    """
    logout(request)
    messages.success(request, "You’ve been signed out.")
    return redirect("home")


@login_required
def account_dashboard(request):
    """
    Simple account dashboard listing the user’s bookings.
    """
    bookings = (
        Booking.objects
        .select_related("car")
        .filter(user=request.user)
        .order_by("-created_at")
    )
    return render(request, "registration/dashboard.html", {"bookings": bookings})
