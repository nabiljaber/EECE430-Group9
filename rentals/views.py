# rentals/views.py
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Car, Dealer, Booking, Favorite, CarImage
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from urllib.parse import urlencode
import calendar
from datetime import date
from decimal import Decimal, InvalidOperation
from .forms import BookingForm, DealerCarForm, PriceForm, DealerApplyForm

INSURANCE_DAILY_FEE = Decimal("20.00")

ACTIVE_BOOKING_STATUSES = [Booking.Status.PENDING, Booking.Status.CONFIRMED]


# ---------------------------
# Public pages
# ---------------------------

def home(request):
    cars = Car.objects.filter(available=True).order_by("-created_at")[:8]
    return render(request, "home.html", {"cars": cars})


def car_list(request):
    qs = Car.objects.filter(available=True).select_related("dealer")

    # Text search: name/title or manufacturer (make)
    q = (request.GET.get("q") or "").strip()
    make = (request.GET.get("make") or "").strip()
    dealer_name = (request.GET.get("dealer") or "").strip()

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(make__icontains=q))
    if make:
        qs = qs.filter(make__icontains=make)
    if dealer_name:
        qs = qs.filter(dealer__name__icontains=dealer_name)

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

    dealer_options = Dealer.objects.filter(active=True).order_by("name").values_list("name", flat=True)

    context = {
        "cars": page.object_list,
        "q": q,
        "type": t,
        "make": make,
        "dealer_name": dealer_name,
        "min_price": min_price_raw,
        "max_price": max_price_raw,
        "sort": sort,
        "result_count": paginator.count,
        "page": page,
        "base_qs": base_qs,
        "base_qs_prefix": base_qs_prefix,
        "dealer_options": dealer_options,
    }
    return render(request, "rentals/car_list.html", context)


def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    form = BookingForm()
    today = timezone.localdate()
    month_start, _ = _month_bounds(today)
    # Build current month + next 12 months (total 12)
    _attach_car_schedule(
        car,
        month_start=month_start,
        months=12,
        today=today,
        upcoming_limit=5,
    )
    context = {
        "car": car,
        "form": form,
        "calendar_month_start": month_start,
        "today": today,
        "upcoming_bookings": getattr(car, "upcoming_bookings", []),
        "is_favorite": Favorite.objects.filter(user=request.user, car=car).exists()
        if request.user.is_authenticated
        else False,
    }
    return render(request, "rentals/car_detail.html", context)


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


def _month_bounds(anchor=None):
    """Return the first day of the month and the first day of the next month."""
    anchor = anchor or timezone.localdate()
    month_start = anchor.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1)
    return month_start, month_end


def _attach_car_schedule(car, *, month_start, today, months=1, upcoming_limit=3):
    """Attach availability info (current/next booking and calendar weeks) to a car."""
    base_qs = (
        Booking.objects
        .filter(car=car, status__in=ACTIVE_BOOKING_STATUSES)
        .select_related("user")
    )
    current = base_qs.filter(
        start_date__lte=today,
        end_date__gte=today,
    ).order_by("start_date").first()
    next_b = base_qs.filter(start_date__gt=today).order_by("start_date").first()
    upcoming_qs = base_qs.filter(start_date__gte=today).order_by("start_date")
    if upcoming_limit is not None:
        upcoming_qs = upcoming_qs[:upcoming_limit]
    upcoming = list(upcoming_qs)
    # Gather bookings during the span we render
    month_ends = []
    m_start = month_start
    for i in range(months):
        _, next_start = _month_bounds(m_start)
        month_ends.append(next_start)
        m_start = next_start
    month_end = month_ends[-1]

    ranges = list(
        base_qs.filter(
            end_date__gte=month_start,
            start_date__lt=month_end,
        ).values("start_date", "end_date")
    )

    months_data = []
    m_start = month_start
    for i in range(months):
        cal = calendar.Calendar(firstweekday=0).monthdatescalendar(m_start.year, m_start.month)
        weeks = []
        for week in cal:
            row = []
            for d in week:
                in_month = (d.month == m_start.month)
                booked = False
                if in_month:
                    for r in ranges:
                        if r["start_date"] <= d <= r["end_date"]:
                            booked = True
                            break
                row.append(
                    {
                        "date": d,
                        "in_month": in_month,
                        "booked": booked,
                        "today": d == today,
                    }
                )
            weeks.append(row)
        months_data.append(
            {
                "label": m_start.strftime("%B %Y"),
                "weeks": weeks,
            }
        )
        # next month start
        if m_start.month == 12:
            m_start = m_start.replace(year=m_start.year + 1, month=1, day=1)
        else:
            m_start = m_start.replace(month=m_start.month + 1, day=1)

    car.current_booking = current
    car.next_booking = next_b
    car.calendar_months = months_data
    car.upcoming_bookings = upcoming


# ---------------------------
# Dealer pages
# ---------------------------

@login_required
@dealer_required
def dealer_dashboard(request):
    dealer = request.user.dealer_profile
    today = timezone.localdate()
    month_start, month_end = _month_bounds(today)
    cars = list(
        dealer.cars
        .annotate(
            confirmed_bookings=Count(
                "bookings",
                filter=Q(bookings__status=Booking.Status.CONFIRMED),
            ),
            confirmed_revenue=Sum(
                "bookings__total_price",
                filter=Q(bookings__status=Booking.Status.CONFIRMED),
            ),
        )
        .order_by("-id")
    )

    # Metrics for current month

    month_bookings = (
        Booking.objects
        .filter(
            car__dealer=dealer,
            start_date__gte=month_start,
            start_date__lt=month_end,
            status__in=ACTIVE_BOOKING_STATUSES,
        )
    )
    pending_bookings = (
        Booking.objects
        .filter(
            car__dealer=dealer,
            status=Booking.Status.PENDING,
        )
        .select_related("car", "user")
        .order_by("start_date", "created_at")
    )
    metrics = month_bookings.aggregate(
        bookings_count=Count("id"),
        revenue=Sum("total_price", filter=Q(status=Booking.Status.CONFIRMED)),
        pending=Count("id", filter=Q(status=Booking.Status.PENDING)),
    )

    # Availability info per car (current status and next booking window)
    for car in cars:
        _attach_car_schedule(
            car,
            month_start=month_start,
            months=3,
            today=today,
            upcoming_limit=4,
        )

    context = {
        "dealer": dealer,
        "cars": cars,
        "metrics": metrics,
        "month_start": month_start,
        "today": today,
        "month_bookings": month_bookings.select_related("car", "user").order_by("start_date"),
        "pending_bookings": pending_bookings,
    }
    return render(request, "dealer/dashboard.html", context)


@login_required
@dealer_required
def dealer_add_car(request):
    dealer = request.user.dealer_profile
    if request.method == "POST":
        form = DealerCarForm(request.POST, request.FILES)
        if form.is_valid():
            car = form.save(commit=False)
            car.dealer = dealer
            car.save()
            uploaded_image = form.cleaned_data.get("image")
            if uploaded_image:
                # Save primary image
                CarImage.objects.create(car=car, image=uploaded_image, is_primary=True)
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
        form = DealerCarForm(request.POST, request.FILES, instance=car)
        if form.is_valid():
            car = form.save()
            uploaded_image = form.cleaned_data.get("image")
            if uploaded_image:
                # If another primary exists, keep it; otherwise set this as primary
                is_primary = not car.images.filter(is_primary=True).exists()
                CarImage.objects.create(car=car, image=uploaded_image, is_primary=is_primary)
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


@login_required
@dealer_required
def dealer_car_bookings(request, pk):
    dealer = request.user.dealer_profile
    car = get_object_or_404(Car, pk=pk, dealer=dealer)
    today = timezone.localdate()
    month_start, month_end = _month_bounds(today)
    _attach_car_schedule(
        car,
        month_start=month_start,
        month_end=month_end,
        today=today,
        upcoming_limit=None,
    )
    bookings = list(
        car.bookings.select_related("user").order_by("-start_date", "-created_at")
    )
    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        action = (request.POST.get("action") or "").lower()
        booking = get_object_or_404(car.bookings, pk=booking_id)
        if action == "confirm" and booking.status != Booking.Status.CONFIRMED:
            booking.status = Booking.Status.CONFIRMED
            booking.save(update_fields=["status"])
            messages.success(request, "Booking confirmed.")
        elif action in {"cancel", "reject"} and booking.status != Booking.Status.CANCELLED:
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["status"])
            messages.info(request, "Booking cancelled.")
        else:
            messages.warning(request, "No changes applied.")
        return redirect("dealer_car_bookings", pk=car.pk)

    return render(
        request,
        "dealer/car_bookings.html",
        {
            "car": car,
            "bookings": bookings,
            "calendar_month_start": month_start,
            "today": today,
        },
    )


@login_required
@dealer_required
def dealer_update_booking_status(request, pk):
    dealer = request.user.dealer_profile
    booking = get_object_or_404(Booking, pk=pk, car__dealer=dealer)
    if request.method != "POST":
        return redirect("dealer_dashboard")
    action = (request.POST.get("action") or "").strip().lower()
    if action == "confirm" and booking.status != Booking.Status.CONFIRMED:
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status"])
        messages.success(request, f"Booking for {booking.car.title} confirmed.")
    elif action in {"cancel", "reject"} and booking.status != Booking.Status.CANCELLED:
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        messages.info(request, f"Booking for {booking.car.title} cancelled.")
    else:
        messages.warning(request, "Nothing to update for this booking.")
    return redirect("dealer_dashboard")


# ---------------------------
# Favorites / wishlist
# ---------------------------

@login_required
def toggle_favorite(request, pk):
    car = get_object_or_404(Car, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, car=car)
    if not created:
        fav.delete()
        messages.info(request, f"Removed {car.title} from your wishlist.")
    else:
        messages.success(request, f"Saved {car.title} to your wishlist.")
    return redirect("car_detail", pk=car.pk)


@login_required
def favorites_list(request):
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("car", "car__dealer")
        .order_by("-created_at")
    )
    return render(request, "rentals/favorites_list.html", {"favorites": favorites})


# ---------------------------
# Booking
# ---------------------------

@login_required
def create_booking(request, pk):
    car = get_object_or_404(Car, pk=pk)

    # Block dealers from booking
    dealer_profile = getattr(request.user, "dealer_profile", None)
    if dealer_profile and dealer_profile.active:
        messages.error(request, "Dealer accounts cannot book cars. Please use a customer account to book.")
        return redirect("car_detail", pk=car.pk)

    form = BookingForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        booking = form.save(commit=False)
        booking.user = request.user
        booking.car = car
        insurance_selected = form.cleaned_data.get("insurance") or False

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
                base_price = days * car.price_per_day
                insurance_fee = days * INSURANCE_DAILY_FEE if insurance_selected else Decimal("0.00")
                booking.total_price = base_price + insurance_fee
                booking.insurance_selected = insurance_selected
                booking.insurance_fee = insurance_fee if insurance_selected else None
                booking.currency = getattr(car, "currency", "USD")
                booking.save()
                messages.success(request, "Booking created. We'll confirm shortly.")
                return redirect("car_detail", pk=car.pk)

    # Re-render detail page with errors or empty form
    return render(request, "rentals/car_detail.html", {"car": car, "form": form})

