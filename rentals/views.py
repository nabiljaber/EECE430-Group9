# rentals/views.py
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Car, Dealer, Booking
from .forms import BookingForm, DealerCarForm, PriceForm, DealerApplyForm


# ---------------------------
# Public pages
# ---------------------------

def home(request):
    cars = Car.objects.filter(available=True).order_by("-created_at")[:8]
    return render(request, "home.html", {"cars": cars})


def car_list(request):
    qs = Car.objects.filter(available=True).order_by("-created_at")
    q = request.GET.get("q", "")
    t = request.GET.get("type", "")
    if q:
        qs = qs.filter(title__icontains=q)
    if t:
        qs = qs.filter(car_type=t)
    return render(request, "rentals/car_list.html", {"cars": qs, "q": q, "type": t})


def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    form = BookingForm()
    return render(request, "rentals/car_detail.html", {"car": car, "form": form})


# ---------------------------
# Dealer utilities / guard
# ---------------------------

def _require_dealer(user) -> bool:
    """Return True if the user has an active dealer profile."""
    return hasattr(user, "dealer_profile") and getattr(user.dealer_profile, "active", False)


def dealer_required(view_fn):
    """Decorator to ensure only authenticated, active dealers can access."""
    @wraps(view_fn)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(next=request.get_full_path())
        if not _require_dealer(request.user):
            raise PermissionDenied("Dealer access required.")
        return view_fn(request, *args, **kwargs)
    return _wrapped


# ---------------------------
# Dealer pages
# ---------------------------

@login_required
@dealer_required
def dealer_dashboard(request):
    dealer = request.user.dealer_profile
    cars = dealer.cars.order_by("-id")
    return render(request, "dealer/dashboard.html", {"dealer": dealer, "cars": cars})


@login_required
@dealer_required
def dealer_add_car(request):
    dealer = request.user.dealer_profile
    if request.method == "POST":
        form = DealerCarForm(request.POST)
        if form.is_valid():
            car = form.save(commit=False)
            car.dealer = dealer
            car.save()
            messages.success(request, "Car added successfully.")
            return redirect("dealer_dashboard")
    else:
        form = DealerCarForm()
    return render(request, "dealer/car_form.html", {"form": form, "title": "Add Car"})


@login_required
@dealer_required
def dealer_update_price(request, pk):
    dealer = request.user.dealer_profile
    car = get_object_or_404(Car, pk=pk, dealer=dealer)  # only your own cars
    if request.method == "POST":
        form = PriceForm(request.POST, instance=car)
        if form.is_valid():
            form.save()
            messages.success(request, "Price updated.")
            return redirect("dealer_dashboard")
    else:
        form = PriceForm(instance=car)
    return render(request, "dealer/price_form.html", {"form": form, "car": car})


# Legacy compatibility: if something still calls 'add_car'
@login_required
def add_car(request):
    if not _require_dealer(request.user):
        raise PermissionDenied("Dealer access required.")
    return dealer_add_car(request)


def dealer_apply(request):
    """Self-serve dealer signup (creates User + Dealer, logs them in)."""
    if request.user.is_authenticated and _require_dealer(request.user):
        return redirect("dealer_dashboard")

    if request.method == "POST":
        form = DealerApplyForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your dealership profile has been created.")
            return redirect("dealer_dashboard")
    else:
        form = DealerApplyForm()
    return render(request, "dealer/apply.html", {"form": form})


# ---------------------------
# Booking
# ---------------------------

@login_required
def create_booking(request, pk):
    car = get_object_or_404(Car, pk=pk)
    form = BookingForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        booking = form.save(commit=False)
        booking.user = request.user
        booking.car = car

        # Basic date checks
        start = booking.start_date
        end = booking.end_date
        today = timezone.localdate()

        if end < start:
            messages.error(request, "End date cannot be before start date.")
        elif start < today:
            messages.error(request, "Start date cannot be in the past.")
        else:
            # Overlap check (pending/confirmed)
            overlap = Booking.objects.filter(
                car=car,
                status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                start_date__lte=end,
                end_date__gte=start,
            ).exists()
            if overlap:
                messages.error(request, "Selected dates overlap with an existing booking.")
            else:
                # Compute total price (at least 1 day)
                days = (end - start).days or 1
                booking.total_price = days * car.price_per_day
                booking.currency = getattr(car, "currency", "USD")
                booking.save()
                messages.success(request, "Booking created. We’ll confirm shortly.")
                return redirect("car_detail", pk=car.pk)

    # Re-render detail page with errors or empty form
    return render(request, "rentals/car_detail.html", {"car": car, "form": form})
