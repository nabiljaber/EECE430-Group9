from django.db import models
from django.contrib.auth.models import User

class Dealer(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    def __str__(self): return self.name

class Car(models.Model):
    TYPES = [('sedan','Sedan'),('suv','SUV'),('hatch','Hatchback'),('van','Van')]
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name='cars')
    title = models.CharField(max_length=150)
    car_type = models.CharField(max_length=10, choices=TYPES, default='sedan')
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.title} ({self.dealer.name})"

class Booking(models.Model):
    STATUS = [('pending','Pending'),('confirmed','Confirmed'),('cancelled','Cancelled')]
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.car.title} | {self.user.username} ({self.status})"
