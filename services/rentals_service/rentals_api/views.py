from datetime import date
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import calendar

from .models import Car, Dealer, Booking, Favorite, CarImage
from .serializers import (
    CarListSerializer,
    CarDetailSerializer,
    BookingSerializer,
    FavoriteSerializer,
    DealerSerializer,
    DealerCarSerializer,
    DealerCarUpdateSerializer,
    DealerDashboardSerializer,
    DealerBookingSerializer,
    DealerCarScheduleSerializer,
    FavoriteListItemSerializer,
)

INSURANCE_DAILY_FEE = Decimal("20.00")
ACTIVE_BOOKING_STATUSES = [Booking.Status.PENDING, Booking.Status.CONFIRMED]


def _month_bounds(anchor=None):
    anchor = anchor or timezone.localdate()
    month_start = anchor.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1)
    return month_start, month_end


def _attach_car_schedule(car, *, month_start, today, months=1, upcoming_limit=3):
    base_qs = (
        Booking.objects
        .filter(car=car, status__in=ACTIVE_BOOKING_STATUSES)
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
    # Build ranges for calendar render
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
        if m_start.month == 12:
            m_start = m_start.replace(year=m_start.year + 1, month=1, day=1)
        else:
            m_start = m_start.replace(month=m_start.month + 1, day=1)

    car.current_booking = current
    car.next_booking = next_b
    car.calendar_months = months_data
    car.upcoming_bookings = upcoming
    if months_data:
        car.calendar_weeks = months_data[0]["weeks"]


@api_view(["GET"])
@permission_classes([AllowAny])
def car_list(request):
    qs = Car.objects.filter(available=True).select_related("dealer")
    q = (request.GET.get("q") or "").strip()
    make = (request.GET.get("make") or "").strip()
    dealer_name = (request.GET.get("dealer") or "").strip()
    t = (request.GET.get("type") or "").strip()
    min_price_raw = (request.GET.get("min_price") or "").strip()
    max_price_raw = (request.GET.get("max_price") or "").strip()

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(make__icontains=q))
    if make:
        qs = qs.filter(make__icontains=make)
    if dealer_name:
        qs = qs.filter(dealer__name__icontains=dealer_name)
    if t:
        qs = qs.filter(car_type=t)
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

    sort = (request.GET.get("sort") or "newest").strip()
    if sort == "price_low":
        qs = qs.order_by("price_per_day", "-created_at")
    elif sort == "price_high":
        qs = qs.order_by("-price_per_day", "-created_at")
    else:
        qs = qs.order_by("-created_at")

    page = int(request.GET.get("page") or 1)
    page_size = 12
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs[start:end]
    data = CarListSerializer(items, many=True, context={"request": request}).data
    return JsonResponse({"results": data, "count": total, "page": page, "pages": (total // page_size) + (1 if total % page_size else 0)})


@api_view(["GET"])
@permission_classes([AllowAny])
def car_detail(request, pk):
    car = get_object_or_404(Car.objects.select_related("dealer"), pk=pk)
    today = timezone.localdate()
    month_start, _ = _month_bounds(today)
    _attach_car_schedule(
        car,
        month_start=month_start,
        months=12,
        today=today,
        upcoming_limit=5,
    )
    data = CarDetailSerializer(car, context={"request": request}).data
    return JsonResponse(data, safe=False)


def _current_user_id(request):
    uid = getattr(request, "user_id", None) or getattr(request.user, "id", None)
    return uid


@api_view(["POST"])
@permission_classes([AllowAny])
def create_booking(request):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    data = request.data
    car_id = data.get("car_id")
    car = get_object_or_404(Car, pk=car_id)

    serializer = BookingSerializer(data=data, context={"request": request})
    if not serializer.is_valid():
        return JsonResponse(serializer.errors, status=400)
    booking = serializer.save(car=car)
    return JsonResponse(BookingSerializer(booking).data, status=201)


@api_view(["GET"])
@permission_classes([AllowAny])
def my_bookings(request):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    bookings = (
        Booking.objects.filter(user_id=uid)
        .select_related("car", "car__dealer")
        .order_by("-start_date", "-created_at")
    )
    data = BookingSerializer(bookings, many=True).data
    return JsonResponse({"results": data})


@api_view(["GET"])
@permission_classes([AllowAny])
def favorites_list(request):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    favorites = (
        Favorite.objects.filter(user_id=uid)
        .select_related("car", "car__dealer")
        .order_by("-created_at")
    )
    data = FavoriteListItemSerializer(favorites, many=True).data
    return JsonResponse({"results": data})


@api_view(["POST"])
@permission_classes([AllowAny])
def toggle_favorite(request):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    car_id = request.data.get("car_id")
    car = get_object_or_404(Car, pk=car_id)
    fav, created = Favorite.objects.get_or_create(user_id=uid, car=car)
    if not created:
        fav.delete()
        return JsonResponse({"is_favorite": False})
    return JsonResponse({"is_favorite": True})


@api_view(["POST"])
@permission_classes([AllowAny])
def dealer_apply(request):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    data = request.data
    required = ["dealership_name", "dealership_email"]
    if any(k not in data or not data[k] for k in required):
        return JsonResponse({"detail": "Missing dealership info."}, status=400)
    dealer, created = Dealer.objects.get_or_create(
        user_id=uid,
        defaults={
            "name": data["dealership_name"],
            "email": data["dealership_email"],
            "phone": data.get("dealership_phone", ""),
            "active": True,
        },
    )
    if not created:
        dealer.name = data["dealership_name"]
        dealer.email = data["dealership_email"]
        dealer.phone = data.get("dealership_phone", "")
        dealer.active = True
        dealer.save()
    return JsonResponse(DealerSerializer(dealer).data, status=201)


@api_view(["GET"])
@permission_classes([AllowAny])
def dealer_dashboard(request):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    dealer = get_object_or_404(Dealer, user_id=uid, active=True)
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
        .select_related("car")
        .order_by("start_date", "created_at")
    )
    metrics = month_bookings.aggregate(
        bookings_count=Count("id"),
        revenue=Sum("total_price", filter=Q(status=Booking.Status.CONFIRMED)),
        pending=Count("id", filter=Q(status=Booking.Status.PENDING)),
    )
    for car in cars:
        _attach_car_schedule(
            car,
            month_start=month_start,
            months=3,
            today=today,
            upcoming_limit=4,
        )
    data = DealerDashboardSerializer(
        {
            "dealer": dealer,
            "cars": cars,
            "metrics": metrics,
            "month_start": month_start,
            "pending_bookings": pending_bookings,
            "month_bookings": month_bookings,
        }
    ).data
    return JsonResponse(data)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def dealer_cars(request):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    dealer = get_object_or_404(Dealer, user_id=uid, active=True)
    if request.method == "GET":
        cars = dealer.cars.all().order_by("-id")
        return JsonResponse(DealerCarSerializer(cars, many=True, context={"request": request}).data, safe=False)

    serializer = DealerCarSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return JsonResponse(serializer.errors, status=400)
    car = serializer.save(dealer=dealer)
    uploaded_image = request.FILES.get("image")
    if uploaded_image:
        CarImage.objects.create(car=car, image=uploaded_image, is_primary=True)
    return JsonResponse(DealerCarSerializer(car, context={"request": request}).data, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def dealer_car_update(request, pk):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    dealer = get_object_or_404(Dealer, user_id=uid, active=True)
    car = get_object_or_404(Car, pk=pk, dealer=dealer)
    if request.method == "DELETE":
        car.delete()
        return JsonResponse({"detail": "deleted"})
    serializer = DealerCarUpdateSerializer(car, data=request.data, partial=True, context={"request": request})
    if not serializer.is_valid():
        return JsonResponse(serializer.errors, status=400)
    car = serializer.save()
    uploaded_image = request.FILES.get("image")
    if uploaded_image:
        is_primary = not car.images.filter(is_primary=True).exists()
        CarImage.objects.create(car=car, image=uploaded_image, is_primary=is_primary)
    return JsonResponse(DealerCarSerializer(car, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def dealer_car_price(request, pk):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    dealer = get_object_or_404(Dealer, user_id=uid, active=True)
    car = get_object_or_404(Car, pk=pk, dealer=dealer)
    serializer = DealerCarUpdateSerializer(car, data={"price_per_day": request.data.get("price_per_day")}, partial=True)
    if not serializer.is_valid():
        return JsonResponse(serializer.errors, status=400)
    serializer.save()
    return JsonResponse({"detail": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def dealer_car_bookings(request, pk):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    dealer = get_object_or_404(Dealer, user_id=uid, active=True)
    car = get_object_or_404(Car, pk=pk, dealer=dealer)
    today = timezone.localdate()
    month_start, month_end = _month_bounds(today)
    _attach_car_schedule(
        car,
        month_start=month_start,
        months=1,
        today=today,
        upcoming_limit=None,
    )
    bookings = list(
        car.bookings.order_by("-start_date", "-created_at")
    )
    return JsonResponse(
        {
            "car": DealerCarScheduleSerializer(car).data,
            "bookings": DealerBookingSerializer(bookings, many=True).data,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def dealer_booking_status(request, booking_id):
    uid = _current_user_id(request)
    if not uid:
        return JsonResponse({"detail": "Unauthorized"}, status=401)
    dealer = get_object_or_404(Dealer, user_id=uid, active=True)
    booking = get_object_or_404(Booking, pk=booking_id, car__dealer=dealer)
    action = (request.data.get("action") or "").strip().lower()
    if action == "confirm" and booking.status != Booking.Status.CONFIRMED:
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status"])
    elif action in {"cancel", "reject"} and booking.status != Booking.Status.CANCELLED:
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
    else:
        return JsonResponse({"detail": "Nothing to update."})
    return JsonResponse({"detail": "ok"})
