from rest_framework import serializers
from .models import Car, Dealer, Booking, Favorite, CarImage
from django.utils import timezone
from decimal import Decimal
from datetime import date


class DealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dealer
        fields = ["id", "name", "email", "phone", "active"]


class CarImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarImage
        fields = ["id", "image", "is_primary"]


class CarListSerializer(serializers.ModelSerializer):
    dealer = DealerSerializer()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = [
            "id",
            "title",
            "car_type",
            "price_per_day",
            "currency",
            "available",
            "year",
            "make",
            "model",
            "color",
            "transmission",
            "seats",
            "doors",
            "mileage_km",
            "location_city",
            "location_country",
            "primary_image",
            "dealer",
        ]

    def get_primary_image(self, obj):
        return obj.primary_image


class BookingSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["id", "start_date", "end_date", "status", "total_price", "currency"]


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "car",
            "start_date",
            "end_date",
            "status",
            "total_price",
            "insurance_selected",
            "insurance_fee",
            "currency",
            "created_at",
            "user_id",
        ]
        read_only_fields = ["status", "total_price", "insurance_fee", "currency", "created_at", "car", "user_id"]

    def validate(self, attrs):
        request = self.context.get("request")
        car_id = request.data.get("car_id")
        if not car_id:
            raise serializers.ValidationError({"car_id": "Car is required."})
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if not start or not end:
            raise serializers.ValidationError("Start and end dates are required.")
        today = timezone.localdate()
        if end < start:
            raise serializers.ValidationError("End date cannot be before start date.")
        if start < today:
            raise serializers.ValidationError("Start date cannot be in the past.")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        from .models import Car, Booking
        car = Car.objects.get(pk=request.data.get("car_id"))
        start = validated_data["start_date"]
        end = validated_data["end_date"]
        overlap = Booking.objects.filter(
            car=car,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_date__lte=end,
            end_date__gte=start,
        ).exists()
        if overlap:
            raise serializers.ValidationError("Selected dates overlap with an existing booking.")
        days = (end - start).days or 1
        insurance = bool(request.data.get("insurance_selected"))
        insurance_fee = days * Decimal("20.00") if insurance else Decimal("0.00")
        total_price = days * car.price_per_day + insurance_fee
        uid = getattr(request.user, "id", None)
        if not uid:
            raise serializers.ValidationError("Unauthorized")
        booking = Booking.objects.create(
            car=car,
            user_id=uid,
            start_date=start,
            end_date=end,
            status=Booking.Status.PENDING,
            total_price=total_price,
            insurance_selected=insurance,
            insurance_fee=insurance_fee if insurance else None,
            currency=car.currency,
        )
        return booking


class CarDetailSerializer(CarListSerializer):
    images = CarImageSerializer(many=True)
    current_booking = BookingSummarySerializer()
    next_booking = BookingSummarySerializer()
    upcoming_bookings = BookingSummarySerializer(many=True)
    calendar_months = serializers.SerializerMethodField()

    class Meta(CarListSerializer.Meta):
        fields = CarListSerializer.Meta.fields + [
            "description",
            "images",
            "current_booking",
            "next_booking",
            "upcoming_bookings",
            "calendar_months",
        ]

    def get_calendar_months(self, obj):
        return getattr(obj, "calendar_months", [])


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "car", "user", "created_at"]


class FavoriteListItemSerializer(serializers.ModelSerializer):
    car = CarListSerializer()

    class Meta:
        model = Favorite
        fields = ["id", "car", "created_at"]


class DealerCarSerializer(serializers.ModelSerializer):
    current_booking = BookingSummarySerializer(read_only=True)
    next_booking = BookingSummarySerializer(read_only=True)
    upcoming_bookings = BookingSummarySerializer(many=True, read_only=True)
    calendar_months = serializers.SerializerMethodField()
    confirmed_revenue = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, read_only=True)
    confirmed_bookings = serializers.IntegerField(required=False, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Car
        fields = [
            "id",
            "title",
            "car_type",
            "price_per_day",
            "currency",
            "description",
            "available",
            "color",
            "make",
            "model",
            "year",
            "transmission",
            "seats",
            "doors",
            "mileage_km",
            "location_city",
            "location_country",
            "current_booking",
            "next_booking",
            "upcoming_bookings",
            "calendar_months",
            "confirmed_revenue",
            "confirmed_bookings",
            "created_at",
        ]
        read_only_fields = [
            "current_booking",
            "next_booking",
            "upcoming_bookings",
            "calendar_months",
            "confirmed_revenue",
            "confirmed_bookings",
            "created_at",
        ]

    def get_calendar_months(self, obj):
        return getattr(obj, "calendar_months", [])


class DealerCarUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = DealerCarSerializer.Meta.fields
        extra_kwargs = {"title": {"required": False}}
        read_only_fields = DealerCarSerializer.Meta.read_only_fields


class DealerDashboardSerializer(serializers.Serializer):
    dealer = DealerSerializer()
    cars = DealerCarSerializer(many=True)
    metrics = serializers.DictField()
    month_start = serializers.DateField()
    pending_bookings = BookingSerializer(many=True)
    month_bookings = BookingSerializer(many=True)


class DealerBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "user_id",
            "start_date",
            "end_date",
            "status",
            "total_price",
            "currency",
            "insurance_selected",
            "insurance_fee",
        ]


class DealerCarScheduleSerializer(serializers.ModelSerializer):
    calendar_months = serializers.SerializerMethodField()
    upcoming_bookings = DealerBookingSerializer(many=True)
    calendar_weeks = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = ["id", "title", "calendar_months", "calendar_weeks", "upcoming_bookings"]

    def get_calendar_months(self, obj):
        return getattr(obj, "calendar_months", [])

    def get_calendar_weeks(self, obj):
        months = getattr(obj, "calendar_months", [])
        if months:
            return months[0].get("weeks")
        return []
