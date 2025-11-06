# rentals/models.py
from django.db import models
from django.conf import settings


# -----------------------------
# Dealer
# -----------------------------
class Dealer(models.Model):
    # One account per dealer (lets us use user.dealer_profile in guards/menus)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="dealer_profile",
    )
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Dealer"
        verbose_name_plural = "Dealers"
        indexes = [models.Index(fields=["active", "name"])]

    def __str__(self):
        return self.name


# -----------------------------
# Car
# -----------------------------
class Car(models.Model):
    TYPES = [
        ("sedan", "Sedan"),
        ("suv", "SUV"),
        ("hatch", "Hatchback"),
        ("van", "Van"),
    ]
    TRANSMISSION = [
        ("AUTO", "Automatic"),
        ("MANUAL", "Manual"),
    ]

    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name="cars")

    title = models.CharField(max_length=150)
    car_type = models.CharField(max_length=10, choices=TYPES, default="sedan")
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    color= models.CharField(max_length=30, blank=True)

    # Optional extras used by UI/filters
    make = models.CharField(max_length=100, blank=True)   # e.g., Toyota
    model = models.CharField(max_length=100, blank=True)  # e.g., Corolla
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    transmission = models.CharField(max_length=10, choices=TRANSMISSION, default="AUTO")
    seats = models.PositiveSmallIntegerField(null=True, blank=True)
    doors = models.PositiveSmallIntegerField(null=True, blank=True)
    mileage_km = models.PositiveIntegerField(null=True, blank=True)

    currency = models.CharField(max_length=3, default="USD")
    location_city = models.CharField(max_length=120, blank=True)
    location_country = models.CharField(max_length=120, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["available", "price_per_day"]),
            models.Index(fields=["car_type", "transmission"]),
            models.Index(fields=["make", "model", "year"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.dealer.name})"


# -----------------------------
# Car images (gallery)
# -----------------------------
class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="images")
    # Requires Pillow if you keep ImageField; otherwise switch to CharField path.
    image = models.ImageField(upload_to="cars/", blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["car", "is_primary"])]

    def __str__(self):
        return f"Image for {self.car.title}"


# -----------------------------
# Booking
# -----------------------------
class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["car", "start_date", "end_date"]),
            models.Index(fields=["user", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F("start_date")),
                name="booking_dates_valid",
            ),
        ]

    def __str__(self):
        return f"{self.car.title} | {self.user} ({self.status})"
