# accounts/views.py
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from rentals.models import Booking
from .forms import (
    AccountUpdateForm,
    DealerUpdateForm,
    SignUpForm,
)

User = get_user_model()


class SignUpView(CreateView):
    model = User
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")


@login_required
def account_dashboard(request):
    bookings = (
        Booking.objects.filter(user=request.user)
        .select_related("car", "car__dealer")
        .order_by("-start_date", "-created_at")
    )
    return render(request, "registration/dashboard.html", {"bookings": bookings})


@login_required
def account_overview(request):
    """
    Account settings page.
    - Always allows editing first_name, last_name, email (username is locked)
    - If the user is a dealer, also show/edit dealership name/email/phone.
    """
    dealer_profile = getattr(request.user, "dealer_profile", None)

    user_form = AccountUpdateForm(request.POST or None, instance=request.user)
    dealer_form = (
        DealerUpdateForm(request.POST or None, instance=dealer_profile)
        if dealer_profile
        else None
    )

    if request.method == "POST":
        user_valid = user_form.is_valid()
        dealer_valid = dealer_form.is_valid() if dealer_form else True

        if user_valid and dealer_valid:
            user_form.save()
            if dealer_form:
                dealer_form.save()
            messages.success(request, "Account details updated.")
            return redirect("account_overview")
    return render(
        request,
        "registration/account_overview.html",
        {"user_form": user_form, "dealer_form": dealer_form, "dealer_profile": dealer_profile},
    )
