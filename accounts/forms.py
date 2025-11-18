from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rentals.models import Dealer

User = get_user_model()

class SignUpForm(UserCreationForm):
    # Make email required and show first/last name fields
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=150)
    last_name = forms.CharField(required=True, max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already in use.")
        return email

    def clean(self):
        data = super().clean()
        # Extra password rule: must not contain first/last name or username
        pwd1 = data.get("password1") or ""
        username = (data.get("username") or "").lower()
        first = (data.get("first_name") or "").lower()
        last = (data.get("last_name") or "").lower()

        # normalize (remove spaces/dots/underscores for stricter test)
        def norm(s): return "".join(ch for ch in s.lower() if ch.isalnum())

        p = norm(pwd1)
        checks = [norm(username), norm(first), norm(last)]
        if any(c and c in p for c in checks):
            raise ValidationError("Password cannot include your name or username.")

        # You already enforce min_length=9 via settings validator
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class DealerUpdateForm(forms.ModelForm):
    class Meta:
        model = Dealer
        fields = ("name", "email", "phone")
        labels = {
            "name": "Dealership name",
            "email": "Dealership email",
            "phone": "Dealership phone",
        }
