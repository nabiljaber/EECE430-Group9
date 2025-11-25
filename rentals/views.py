# rentals/views.py

from functools import wraps
from types import SimpleNamespace

from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import date as date_cls

from .models import Car

from ajerlo import api_client
from .forms import BookingForm, DealerCarForm, PriceForm
import json


def _token(request):
    return request.COOKIES.get("auth_token")


def _add_pk(obj):
    """Ensure API dicts have pk attribute for templates that expect it, and coerce calendar dates."""
    if isinstance(obj, dict):
        if "id" in obj and "pk" not in obj:
            obj["pk"] = obj["id"]
        for k, v in list(obj.items()):
            if k == "calendar_months" and isinstance(v, list):
                for month in v:
                    if isinstance(month, dict) and isinstance(month.get("weeks"), list):
                        for week in month["weeks"]:
                            for day in week:
                                if isinstance(day, dict) and isinstance(day.get("date"), str):
                                    try:
                                        day["date"] = date_cls.fromisoformat(day["date"])
                                    except Exception:
                                        pass
            obj[k] = _add_pk(v)
    elif isinstance(obj, list):
        return [_add_pk(x) for x in obj]
    return obj


def _ns(obj):
    """Recursively convert dicts to SimpleNamespace for template dot access."""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_ns(x) for x in obj]
    return obj


def home(request):
    # local import to guarantee Car is defined
    from .models import Car

    cars = Car.objects.order_by("-id")[:8]  # newest 8 cars
    return render(request, "home.html", {"cars": cars})



def car_list(request):
    qs = Car.objects.all().order_by("-id")

    q = request.GET.get("q") or ""
    if q:
        qs = qs.filter(title__icontains=q)

    cars = qs  # you can add more filters later

    context = {
        "cars": cars,
        "q": q,
        "type": request.GET.get("type") or "",
        "make": request.GET.get("make") or "",
        "dealer_name": request.GET.get("dealer") or "",
        "min_price": request.GET.get("min_price") or "",
        "max_price": request.GET.get("max_price") or "",
        "sort": request.GET.get("sort") or "newest",
        "result_count": cars.count(),
        "page": SimpleNamespace(
            object_list=list(cars),
            number=1,
            paginator=SimpleNamespace(num_pages=1, page_range=[1]),
            has_previous=False,
            has_next=False,
            previous_page_number=1,
            next_page_number=1,
        ),
        "base_qs": "",
        "base_qs_prefix": "q=",
        "dealer_options": [],
    }
    return render(request, "rentals/car_list.html", context)


def car_detail(request, pk):
    token = _token(request)
    try:
        car = _add_pk(api_client.rentals_detail(pk, token=token))
    except Exception:
        messages.error(request, "Car not found.")
        return redirect("car_list")
    form = BookingForm()
    context = {
        "car": SimpleNamespace(**car),
        "form": form,
        "calendar_month_start": timezone.localdate().replace(day=1),
        "today": timezone.localdate(),
        "upcoming_bookings": car.get("upcoming_bookings", []),
        "is_favorite": False,
    }
    return render(request, "rentals/car_detail.html", context)


# ---------------------------
# Dealer utilities / guard
# ---------------------------

def _require_dealer(user) -> bool:
    """Return True if the user has an active dealer profile."""
    if hasattr(user, "dealer_profile") and getattr(user.dealer_profile, "active", False):
        return True
    if getattr(user, "is_dealer", False):
        return True
    return False


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
        is_dealer = (
            _require_dealer(request.user)
            or request.COOKIES.get("is_dealer") in {"true", "1", "yes", "on"}
            or getattr(request.user, "is_dealer", False)
        )

        # If token exists but flag is missing, verify with rentals service and promote.
        promoted = False
        token = _token(request)
        if not is_dealer and token:
            try:
                # Will raise if unauthorized/not dealer
                api_client.rentals_dealer_dashboard(token)
                is_dealer = True
                promoted = True
                if hasattr(request, "user"):
                    request.user.is_dealer = True
            except Exception:
                is_dealer = False

        if not is_dealer:
            messages.info(request, "Dealer access required. Apply to become a dealer.")
            return redirect("dealer_apply")

        response = view_fn(request, *args, **kwargs)
        if promoted and hasattr(response, "set_cookie"):
            response.set_cookie("is_dealer", "true", httponly=True, samesite="Lax")
        return response

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

@dealer_required
def dealer_dashboard(request):
    token = _token(request)
    if not token:
        return redirect("login")
    try:
        data = _add_pk(api_client.rentals_dealer_dashboard(token))
    except Exception:
        messages.error(request, "Could not load dealer dashboard.")
        return redirect("home")
    dealer = _ns(data.get("dealer", {}))
    cars = _ns(data.get("cars", []))
    metrics = data.get("metrics", {})
    pending_bookings = _ns(data.get("pending_bookings", []))
    month_bookings = _ns(data.get("month_bookings", []))
    month_start = data.get("month_start")
    today = timezone.localdate()
    # Populate user placeholder to avoid template errors
    def _attach_user(obj):
        if isinstance(obj, list):
            for b in obj:
                _attach_user(b)
        else:
            if getattr(obj, "user", None) is None and getattr(obj, "user_id", None) is not None:
                obj.user = SimpleNamespace(username=f"User {obj.user_id}", email="", get_full_name=lambda: f"User {obj.user_id}")
    _attach_user(month_bookings)
    _attach_user(pending_bookings)
    for car in cars:
        _attach_user(getattr(car, "upcoming_bookings", []))
        if getattr(car, "next_booking", None):
            _attach_user(car.next_booking)
    return render(
        request,
        "dealer/dashboard.html",
        {
            "dealer": dealer,
            "cars": cars,
            "metrics": metrics,
            "month_start": month_start,
            "today": today,
            "month_bookings": month_bookings,
            "pending_bookings": pending_bookings,
        },
    )


@dealer_required
def dealer_add_car(request):
    token = _token(request)
    if not token:
        return redirect("login")
    form = DealerCarForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        # Build payload excluding CSRF and file
        payload = {
            k: v
            for k, v in form.data.items()
            if k not in {"csrfmiddlewaretoken", "image"}
        }
        files = {}
        if request.FILES.get("image"):
            files["image"] = request.FILES.get("image")
        resp = api_client.rentals_dealer_car_create(token, payload, files=files)
        if resp.status_code in (200, 201):
            messages.success(request, "Car added successfully.")
            return redirect("dealer_dashboard")
        else:
            try:
                detail = resp.json().get("detail") or "Could not add car."
            except Exception:
                detail = "Could not add car."
            messages.error(request, detail)
    return render(request, "dealer/car_form.html", {"form": form, "title": "Add Car"})

# rentals/views.py
@dealer_required
def dealer_edit_car(request, pk):
    token = _token(request)
    if not token:
        return redirect("login")
    # Prefill using car list lookup
    initial = None
    if request.method != "POST":
        try:
            cars = api_client.rentals_dealer_car_list(token)
            for car in cars:
                if str(car.get("id")) == str(pk):
                    initial = car
                    break
        except Exception:
            pass
    form = DealerCarForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        resp = api_client.rentals_dealer_car_update(token, pk, form.data, files=request.FILES)
        if resp.status_code in (200, 201):
            messages.success(request, "Car updated.")
            return redirect("dealer_dashboard")
        else:
            try:
                detail = resp.json().get("detail") or "Could not update car."
            except Exception:
                detail = "Could not update car."
            messages.error(request, detail)
    return render(request, "dealer/car_form.html", {"form": form, "title": "Edit Car"})

@dealer_required
def dealer_delete_car(request, pk):
    token = _token(request)
    if not token:
        return redirect("login")
    api_client.rentals_dealer_car_delete(token, pk)
    messages.success(request, "Car deleted.")
    return redirect("dealer_dashboard")



@dealer_required
def dealer_update_price(request, pk):
    token = _token(request)
    if not token:
        return redirect("login")
    initial_price = None
    if request.method != "POST":
        try:
            cars = api_client.rentals_dealer_car_list(token)
            for car in cars:
                if str(car.get("id")) == str(pk):
                    initial_price = car.get("price_per_day")
                    break
        except Exception:
            pass
    form = PriceForm(request.POST or None, initial={"price_per_day": initial_price} if initial_price else None)
    if request.method == "POST" and form.is_valid():
        resp = api_client.rentals_dealer_price(token, pk, {"price_per_day": form.cleaned_data["price_per_day"]})
        if resp.status_code in (200, 201):
            messages.success(request, "Price updated.")
            return redirect("dealer_dashboard")
        else:
            messages.error(request, "Could not update price.")
    return render(request, "dealer/price_form.html", {"form": form, "car": SimpleNamespace(id=pk, title="")})


# Legacy compatibility: if something still calls 'add_car'
def add_car(request):
    if not _require_dealer(request.user):
        raise PermissionDenied("Dealer access required.")
    return dealer_add_car(request)


@dealer_required
def dealer_car_bookings(request, pk):
    token = _token(request)
    if not token:
        return redirect("login")
    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        action = (request.POST.get("action") or "").lower()
        if booking_id and action:
            api_client.rentals_dealer_booking_status(token, booking_id, action)
            messages.success(request, "Updated booking.")
        return redirect("dealer_car_bookings", pk=pk)
    try:
        data = _add_pk(api_client.rentals_dealer_car_bookings(token, pk))
    except Exception:
        messages.error(request, "Could not load car bookings. Make sure this car exists.")
        return redirect("dealer_dashboard")
    car = _ns(data.get("car", {}))
    bookings = _ns(data.get("bookings", []))
    # Attach placeholder user info
    def _attach_user(obj):
        if getattr(obj, "user", None) is None and getattr(obj, "user_id", None) is not None:
            obj.user = SimpleNamespace(username=f"User {obj.user_id}", email="", get_full_name=lambda: f"User {obj.user_id}")
    for b in bookings:
        _attach_user(b)
    if getattr(car, "upcoming_bookings", None):
        for b in car.upcoming_bookings:
            _attach_user(b)
    # Also attach placeholder for calendar weeks/upcoming
    if getattr(car, "calendar_months", None):
        for month in car.calendar_months:
            if isinstance(month, dict) and isinstance(month.get("bookings"), list):
                for b in month["bookings"]:
                    _attach_user(b)
    return render(
        request,
        "dealer/car_bookings.html",
        {
            "car": car,
            "bookings": bookings,
            "calendar_month_start": getattr(car.calendar_months[0], "label", None) if getattr(car, "calendar_months", None) else None,
            "today": timezone.localdate(),
        },
    )


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

def toggle_favorite(request, pk):
    token = _token(request)
    if not token:
        return redirect("login")
    api_client.rentals_toggle_favorite(token, pk)
    return redirect("car_detail", pk=pk)


def favorites_list(request):
    token = _token(request)
    if not token:
        return redirect("login")
    favorites = _add_pk(api_client.rentals_favorites(token))
    return render(request, "rentals/favorites_list.html", {"favorites": favorites})


def dealer_apply(request):
    class DealerApplyForm(forms.Form):
        # Account
        username = forms.CharField(max_length=150, required=True)
        email = forms.EmailField(required=True)
        first_name = forms.CharField(max_length=150, required=False)
        last_name = forms.CharField(max_length=150, required=False)
        password1 = forms.CharField(widget=forms.PasswordInput, required=True)
        password2 = forms.CharField(widget=forms.PasswordInput, required=True)
        # Dealer
        dealership_name = forms.CharField(max_length=150, required=True)
        dealership_email = forms.EmailField(required=True)
        dealership_phone = forms.CharField(max_length=30, required=False)

        def __init__(self, *args, require_account=True, **kwargs):
            super().__init__(*args, **kwargs)
            if not require_account:
                for f in ["username", "email", "password1", "password2", "first_name", "last_name"]:
                    self.fields[f].required = False

        def clean(self):
            data = super().clean()
            p1 = data.get("password1")
            p2 = data.get("password2")
            if self.fields["password1"].required:
                if p1 and p2 and p1 != p2:
                    self.add_error("password2", "Passwords do not match.")
            return data

    token = _token(request)
    require_account = token is None
    form = DealerApplyForm(request.POST or None, require_account=require_account)
    if request.method == "POST" and form.is_valid():
        # Create account if needed
        if require_account:
            acct_payload = {
                "username": form.cleaned_data["username"],
                "email": form.cleaned_data["email"],
                "first_name": form.cleaned_data.get("first_name", ""),
                "last_name": form.cleaned_data.get("last_name", ""),
                "password": form.cleaned_data["password1"],
            }
            data, err = api_client.accounts_signup(acct_payload)
            if err or not data:
                form.add_error(None, err.get("detail", "Signup failed.") if err else "Signup failed.")
                return render(request, "dealer/apply.html", {"form": form, "require_account": require_account})
            token = data.get("token")

        dealer_payload = {
            "dealership_name": form.cleaned_data["dealership_name"],
            "dealership_email": form.cleaned_data["dealership_email"],
            "dealership_phone": form.cleaned_data.get("dealership_phone", ""),
        }
        resp = api_client.rentals_dealer_apply(token, dealer_payload)
        if resp.status_code in (200, 201):
            messages.success(request, "Dealer profile created. You can now add cars.")
            resp_redirect = redirect("dealer_dashboard")
            if token:
                resp_redirect.set_cookie("auth_token", token, httponly=True, samesite="Lax")
            resp_redirect.set_cookie("is_dealer", "true", httponly=True, samesite="Lax")
            return resp_redirect
        else:
            # If token is bad/expired, clear it and ask user to log in again.
            if resp.status_code in (401, 403):
                messages.error(request, "Session expired. Please log in again to create your dealer profile.")
                resp_redirect = redirect("login")
                resp_redirect.delete_cookie("auth_token")
                resp_redirect.delete_cookie("is_dealer")
                return resp_redirect
            try:
                detail = resp.json().get("detail") or "Could not create dealer profile."
            except Exception:
                detail = "Could not create dealer profile."
            form.add_error(None, detail)

    return render(request, "dealer/apply.html", {"form": form, "require_account": require_account})


# ---------------------------
# Booking
# ---------------------------

def create_booking(request, pk):
    token = _token(request)
    if not token:
        return redirect("login")
    try:
        car = _add_pk(api_client.rentals_detail(pk, token=token))
    except Exception:
        messages.error(request, "Car not found.")
        return redirect("car_list")
    form = BookingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        payload = {
            "car_id": pk,
            "start_date": form.cleaned_data["start_date"].isoformat(),
            "end_date": form.cleaned_data["end_date"].isoformat(),
            "insurance_selected": form.cleaned_data.get("insurance_selected") or False,
        }
        resp = api_client.rentals_booking_create(token, payload)
        if resp.status_code == 201:
            messages.success(request, "Booking created. We'll confirm shortly.")
            return redirect("car_detail", pk=pk)
        else:
            # Handle auth expiry
            if resp.status_code in (401, 403):
                messages.error(request, "Session expired. Please log in and try again.")
                resp_redirect = redirect("login")
                resp_redirect.delete_cookie("auth_token")
                resp_redirect.delete_cookie("is_dealer")
                return resp_redirect
            # Surface API validation errors to the user
            msg = "Could not create booking."
            try:
                data = resp.json()
                if isinstance(data, dict):
                    if "detail" in data:
                        msg = data["detail"]
                    elif any(isinstance(v, list) for v in data.values()):
                        parts = []
                        for k, v in data.items():
                            if isinstance(v, list):
                                parts.append(f"{k}: {'; '.join(str(x) for x in v)}")
                        if parts:
                            msg = "; ".join(parts)
                elif isinstance(data, list):
                    msg = "; ".join(str(x) for x in data)
                elif isinstance(data, str):
                    msg = data
            except Exception:
                pass
            messages.error(request, msg)
    return render(request, "rentals/car_detail.html", {"car": SimpleNamespace(**car), "form": form})

