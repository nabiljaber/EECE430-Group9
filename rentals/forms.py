<<<<<<< HEAD
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
    # account fields
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    # dealership fields
    dealer_name = forms.CharField(label="Dealership name", max_length=150)
    phone = forms.CharField(label="Phone", max_length=30, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean(self):
        cleaned = super().clean()  # keeps default username/password matching validation
        p2 = (cleaned.get("password2") or "").strip()

        # Enforce min length
        if p2 and len(p2) < 9:
            self.add_error("password2", "Password must be at least 9 characters long.")

        # Must not include username or (parts of) the person's name
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
                active=True,  # set to False if you want manual approval
            )
        return user


# ---------------------------
# Dealer car management
# ---------------------------
class DealerCarForm(forms.ModelForm):
    """Used by a dealer to create a car (the view sets car.dealer)."""
    class Meta:
        model = Car
        fields = ("title", "description", "price_per_day")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g., Toyota Corolla 2020"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Condition, mileage, features…"}),
            "price_per_day": forms.NumberInput(attrs={"step": "0.01"}),
        }


class PriceForm(forms.ModelForm):
    """Dealer can update only the price."""
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


# ---------------------------
# (Optional) Legacy add_car path
# ---------------------------
class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ("title", "car_type", "description", "price_per_day", "available")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price_per_day": forms.NumberInput(attrs={"step": "0.01"}),
=======
from django import forms
from .models import Car, Booking

class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ["dealer","title","car_type","price_per_day","description","available"]

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["start_date","end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type":"date"}),
            "end_date": forms.DateInput(attrs={"type":"date"}),
>>>>>>> 75f6ec464013ed4df1d1158a123edad786a0c61a
        }
