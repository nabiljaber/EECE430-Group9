# rentals/views.py
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Car, Dealer, Booking
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from urllib.parse import urlencode
import calendar
from datetime import date
from decimal import Decimal, InvalidOperation
from .forms import BookingForm, DealerCarForm, PriceForm, DealerApplyForm


# ---------------------------
# Public pages
# ---------------------------

def home(request):
    cars = Car.objects.filter(available=True).order_by("-created_at")[:8]
    return render(request, "home.html", {"cars": cars})


def car_list(request):
    qs = Car.objects.filter(available=True)

    # Text search: name/title or manufacturer (make)
    q = (request.GET.get("q") or "").strip()
    make = (request.GET.get("make") or "").strip()

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(make__icontains=q))
    if make:
        qs = qs.filter(make__icontains=make)

    # Type filter
    t = (request.GET.get("type") or "").strip()
    if t:
        qs = qs.filter(car_type=t)

    # Price range filters
    min_price_raw = (request.GET.get("min_price") or "").strip()
    max_price_raw = (request.GET.get("max_price") or "").strip()
    try:
        if min_price_raw:
            qs = qs.filter(price_per_day__gte=Decimal(min_price_raw))
    except (InvalidOperation, ValueError):
        pass
    try:
        if max_price_raw:
            qs = qs.filter(price_per_day__lte=Decimal(max_price_raw))
    except (InvalidOperation, ValueError):
        pass

    # Sorting
    sort = (request.GET.get("sort") or "newest").strip()
    if sort == "price_low":
        qs = qs.order_by("price_per_day", "-created_at")
    elif sort == "price_high":
        qs = qs.order_by("-price_per_day", "-created_at")
    else:
        sort = "newest"
    qs = qs.order_by("-created_at")

    # Pagination (12 per page)
    paginator = Paginator(qs, 12)
    page_num = request.GET.get("page") or 1
    page = paginator.get_page(page_num)

    # Base querystring without page for cleaner pagination links
    qd = request.GET.copy()
    qd.pop("page", None)
    base_qs = urlencode(list(qd.lists()), doseq=True)
    base_qs_prefix = (base_qs + "&") if base_qs else ""

    context = {
        "cars": page.object_list,
        "q": q,
        "type": t,
        "make": make,
        "min_price": min_price_raw,
        "max_price": max_price_raw,
        "sort": sort,
        "result_count": paginator.count,
        "page": page,
        "base_qs": base_qs,
        "base_qs_prefix": base_qs_prefix,
    }
    return render(request, "rentals/car_list.html", context)


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
    """Decorator to ensure only authenticated, active dealers can access.

    UX: if the user is logged in but not a dealer, redirect to the dealer
    application page with a friendly message instead of a 403 page.
    """
    @wraps(view_fn)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(next=request.get_full_path())
        if not _require_dealer(request.user):
            messages.info(request, "Dealer access required. Apply to become a dealer.")
            return redirect("dealer_apply")
        return view_fn(request, *args, **kwargs)
    return _wrapped


# ---------------------------
# Dealer pages
# ---------------------------

@login_required
@dealer_required
def dealer_dashboard(request):
    dealer = request.user.dealer_profile
    cars = list(dealer.cars.order_by("-id"))

    # Metrics for current month
    today = timezone.localdate()
    month_start = today.replace(day=1)
    # Naive month end calculation
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year+1, month=1, day=1)
    else:
        month_end = month_start.replace(month=month_start.month+1, day=1)

    month_bookings = (
        Booking.objects
        .filter(car__dealer=dealer,
                start_date__gte=month_start,
                start_date__lt=month_end,
                status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED])
    )
    metrics = month_bookings.aggregate(
        bookings_count=Count("id"),
        revenue=Sum("total_price")
    )

    # Availability info per car (current status and next booking window)
    for car in cars:
        current = Booking.objects.filter(
            car=car,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_date__lte=today,
            end_date__gte=today,
        ).order_by("start_date").first()
        next_b = (
            Booking.objects
            .filter(car=car,
                    status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                    start_date__gt=today)
            .order_by("start_date")
            .first()
        )
        # attach for easy template access without custom tags
        car.current_booking = current
        car.next_booking = next_b

        # Build a mini calendar (current month) with booked days highlighted
        month_weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year, month_start.month)
        # Ranges overlapping the month
        ranges = list(Booking.objects.filter(
            car=car,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            end_date__gte=month_start,
            start_date__lt=month_end,
        ).values("start_date", "end_date"))

        weeks = []
        for week in month_weeks:
            row = []
            for d in week:
                in_month = (d.month == month_start.month)
                booked = False
                if in_month:
                    for r in ranges:
                        if r["start_date"] <= d <= r["end_date"]:
                            booked = True
                            break
                row.append({
                    "date": d,
                    "in_month": in_month,
                    "booked": booked,
                    "today": d == today,
                })
            weeks.append(row)
        car.calendar_weeks = weeks

    context = {
        "dealer": dealer,
        "cars": cars,
        "metrics": metrics,
        "month_start": month_start,
        "today": today,
        "month_bookings": month_bookings.select_related("car", "user").order_by("start_date"),
    }
    return render(request, "dealer/dashboard.html", context)


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

# rentals/views.py
@login_required
@dealer_required
def dealer_edit_car(request, pk):
    dealer = request.user.dealer_profile
    car = get_object_or_404(Car, pk=pk, dealer=dealer)
    if request.method == "POST":
        form = DealerCarForm(request.POST, instance=car)
        if form.is_valid():
            form.save()
            messages.success(request, "Car updated.")
            return redirect("dealer_dashboard")
    else:
        form = DealerCarForm(instance=car)
    return render(request, "dealer/car_form.html", {"form": form, "title": "Edit Car"})

@login_required
@dealer_required
def dealer_delete_car(request, pk):
    dealer = request.user.dealer_profile
    car = get_object_or_404(Car, pk=pk, dealer=dealer)
    if request.method == "POST":
        car.delete()
        messages.success(request, "Car deleted.")
        return redirect("dealer_dashboard")
    # optional confirm page could go here; for now, redirect to dashboard
    return redirect("dealer_dashboard")



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
