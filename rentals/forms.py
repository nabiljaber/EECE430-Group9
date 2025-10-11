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
        }
