# accounts/views.py
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
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
    messages.success(request, "You've been signed out.")
    return redirect("home")


@login_required
def account_dashboard(request):
    """
    Richer account dashboard showing upcoming trips and history.
    """
    bookings_qs = (
        Booking.objects
        .select_related("car", "car__dealer")
        .filter(user=request.user)
        .order_by("start_date")
    )
    metrics_raw = bookings_qs.aggregate(
        total_spent=Sum("total_price"),
        confirmed_count=Count("id", filter=Q(status=Booking.Status.CONFIRMED)),
        pending_count=Count("id", filter=Q(status=Booking.Status.PENDING)),
        cancelled_count=Count("id", filter=Q(status=Booking.Status.CANCELLED)),
    )
    bookings = list(bookings_qs)
    today = timezone.localdate()
    upcoming_bookings = [b for b in bookings if b.start_date >= today]
    past_bookings = [b for b in bookings if b.start_date < today]
    context = {
        "bookings": bookings,
        "upcoming_bookings": upcoming_bookings,
        "past_bookings": past_bookings,
        "next_booking": upcoming_bookings[0] if upcoming_bookings else None,
        "metrics": {
            "total": len(bookings),
            "upcoming": len(upcoming_bookings),
            "total_spent": metrics_raw.get("total_spent") or 0,
            "confirmed": metrics_raw.get("confirmed_count") or 0,
            "pending": metrics_raw.get("pending_count") or 0,
            "cancelled": metrics_raw.get("cancelled_count") or 0,
        },
        "today": today,
    }
    return render(request, "registration/dashboard.html", context)
