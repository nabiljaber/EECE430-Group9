# rentals/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import Car, Booking, Dealer, CarImage

User = get_user_model()

# ---------------------------
# Dealer self-serve signup
# ---------------------------
class DealerApplyForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    dealership_name = forms.CharField(
        max_length=150,
        help_text="Public name of your dealership as customers will see it.",
        label="Dealership name",
    )
    dealership_email = forms.EmailField(
        help_text="Contact email shown on your profile and used for notifications.",
        label="Dealership email",
    )
    dealership_phone = forms.CharField(
        max_length=30,
        required=False,
        help_text="Optional phone number for customer contact.",
        label="Dealership phone",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")

        if commit:
            user.save()

            Dealer.objects.create(
                user=user,
                name=self.cleaned_data["dealership_name"],
                email=self.cleaned_data["dealership_email"],
                phone=self.cleaned_data.get("dealership_phone", ""),
                active=True,
            )

        return user


# ---------------------------
# Dealer car management form
# ---------------------------
class DealerCarForm(forms.ModelForm):
    # Extra field for uploading a main photo (stored via CarImage in views)
    image = forms.ImageField(required=False, label="Main photo")

    class Meta:
        model = Car
        fields = (
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
        )
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Tell customers what makes this car special, conditions, mileage, pickup notes…",
                }
            ),
            "price_per_day": forms.NumberInput(attrs={"step": "0.01"}),
            "year": forms.NumberInput(attrs={"min": 1980, "max": 2100}),
        }

    def clean_year(self):
        year = self.cleaned_data.get("year")
        if year and (year < 1980 or year > 2100):
            raise forms.ValidationError("Please enter a reasonable year.")
        return year


class PriceForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ("price_per_day",)
        widgets = {
            "price_per_day": forms.NumberInput(attrs={"step": "0.01"}),
        }


# ---------------------------
# Booking form
# ---------------------------
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("start_date", "end_date", "insurance_selected")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "insurance_selected": "Add insurance coverage ($20/day)",
        }
        help_texts = {
            "insurance_selected": "Includes damage protection and roadside assistance.",
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

class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
