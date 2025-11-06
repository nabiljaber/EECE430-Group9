# rentals/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import Car, Booking, Dealer

User = get_user_model()

# ---------------------------
# Dealer self-serve signup
# ---------------------------
class DealerApplyForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    dealer_name = forms.CharField(label="Dealership name", max_length=150)
    phone = forms.CharField(label="Phone", max_length=30, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean(self):
        cleaned = super().clean()
        p2 = (cleaned.get("password2") or "").strip()

        if p2 and len(p2) < 9:
            self.add_error("password2", "Password must be at least 9 characters long.")

        tokens = [
            (cleaned.get("username") or "").strip(),
            (cleaned.get("first_name") or "").strip(),
            (cleaned.get("last_name") or "").strip(),
        ]
        p2_lower = p2.lower()
        for t in tokens:
            t = t.lower()
            if t and len(t) >= 3 and t in p2_lower:
                self.add_error("password2", "Password cannot contain your name or username.")
                break
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            Dealer.objects.create(
                user=user,
                name=self.cleaned_data["dealer_name"],
                email=user.email,
                phone=self.cleaned_data.get("phone", ""),
                active=True,
            )
        return user


# ---------------------------
# Dealer car management (uses Car.available)
# ---------------------------
class DealerCarForm(forms.ModelForm):
    """Used by a dealer to create/update a car (the view sets car.dealer)."""
    class Meta:
        model = Car
        fields = [
            "title",
            "make", "model", "year", "color",
            "car_type", "transmission",
            "seats", "doors", "mileage_km",
            "price_per_day", "currency",
            "location_city", "location_country",
            "available",
        ]
        labels = {
            "title": "Listing title",
            "make": "Make",
            "model": "Model",
            "year": "Year",
            "color": "Color",
            "car_type": "Car type",
            "transmission": "Transmission",
            "seats": "Seats",
            "doors": "Doors",
            "mileage_km": "Mileage (km)",
            "price_per_day": "Price per day",
            "currency": "Currency",
            "location_city": "City",
            "location_country": "Country",
            "available": "Show this car in search",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Toyota Corolla 2020"}),
            "make": forms.TextInput(attrs={"placeholder": "e.g. Toyota"}),
            "model": forms.TextInput(attrs={"placeholder": "e.g. Corolla"}),
            "year": forms.NumberInput(attrs={"min": 1980, "max": 2100}),
            "color": forms.TextInput(attrs={"placeholder": "e.g. White"}),
            "seats": forms.NumberInput(attrs={"min": 1, "max": 9}),
            "doors": forms.NumberInput(attrs={"min": 2, "max": 6}),
            "mileage_km": forms.NumberInput(attrs={"min": 0, "step": 1000}),
            "price_per_day": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "currency": forms.TextInput(attrs={"maxlength": 3, "placeholder": "USD"}),
            "location_city": forms.TextInput(attrs={"placeholder": "e.g. Beirut"}),
            "location_country": forms.TextInput(attrs={"placeholder": "e.g. Lebanon"}),
        }


class PriceForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ("price_per_day",)
        widgets = {"price_per_day": forms.NumberInput(attrs={"step": "0.01"})}


# ---------------------------
# Booking
# ---------------------------
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("start_date", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


# Legacy (kept)
class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ("title", "car_type", "description", "price_per_day", "available")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price_per_day": forms.NumberInput(attrs={"step": "0.01"}),
        }
