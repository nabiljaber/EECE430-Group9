# accounts/views.py
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView
from django import forms
from types import SimpleNamespace

from ajerlo import api_client
import requests


def _token(request):
    return request.COOKIES.get("auth_token")


class SignUpForm(forms.Form):
    first_name = forms.CharField(required=True, max_length=150)
    last_name = forms.CharField(required=True, max_length=150)
    username = forms.CharField(required=True, max_length=150)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password2") and data["password1"] != data["password2"]:
            self.add_error("password2", "Passwords do not match.")
        return data


class SignUpView(FormView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        payload = {
            "first_name": form.cleaned_data["first_name"],
            "last_name": form.cleaned_data["last_name"],
            "username": form.cleaned_data["username"],
            "email": form.cleaned_data["email"],
            "password": form.cleaned_data["password1"],
        }
        try:
            data, err = api_client.accounts_signup(payload)
        except Exception:
            err = {"detail": "Signup service unavailable."}
            data = None
        if err:
            form.add_error(None, err.get("detail", "Signup failed"))
            return self.form_invalid(form)
        resp = redirect(self.get_success_url())
        resp.set_cookie("auth_token", data["token"], httponly=True, samesite="Lax")
        # New account is not a dealer yet; clear any stale cookie
        resp.delete_cookie("is_dealer")
        return resp


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            data, err = api_client.accounts_login(
                form.cleaned_data["username"], form.cleaned_data["password"]
            )
        except Exception as e:
            err = {"detail": "Login service unavailable."}
            data = None
        if err or not data:
            form.add_error(None, err.get("detail", "Invalid credentials.") if err else "Invalid credentials.")
        else:
            # Default redirect target
            next_url = request.GET.get("next")
            # Clear any previous dealer flag
            is_dealer = False
            try:
                r = requests.get(f"{api_client.RENTALS_API}/dealer/dashboard/", headers=api_client._headers(data["token"]), timeout=5)
                is_dealer = (r.status_code == 200)
            except Exception:
                is_dealer = False

            # If dealer, default redirect to dashboard unless a next is provided
            if is_dealer and not next_url:
                next_url = "dealer_dashboard"

            resp = redirect(next_url or "home")
            resp.set_cookie("auth_token", data["token"], httponly=True, samesite="Lax")
            resp.delete_cookie("is_dealer")
            if is_dealer:
                resp.set_cookie("is_dealer", "true", httponly=True, samesite="Lax")
            return resp
    return render(request, "registration/login.html", {"form": form})


def account_dashboard(request):
    token = _token(request)
    if not token:
        return redirect("login")
    def _ns(obj):
        if isinstance(obj, dict):
            return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
        if isinstance(obj, list):
            return [_ns(x) for x in obj]
        return obj

    try:
        bookings_raw = api_client.rentals_my_bookings(token)
    except Exception:
        bookings_raw = []
        messages.error(request, "Could not load bookings.")

    bookings = []
    for b in bookings_raw:
        car_id = b.get("car")
        car_data = None
        if car_id:
            try:
                car_data = api_client.rentals_detail(car_id, token=token)
            except Exception:
                car_data = {"id": car_id, "title": f"Car #{car_id}", "dealer": {"name": "", "email": ""}}
        if not car_data:
            car_data = {"id": car_id, "title": f"Car #{car_id}", "dealer": {"name": "", "email": ""}}
        if "id" in car_data and "pk" not in car_data:
            car_data["pk"] = car_data["id"]
        if "dealer" in car_data and isinstance(car_data["dealer"], dict):
            car_data["dealer"].setdefault("name", "")
            car_data["dealer"].setdefault("email", "")
        b["car"] = car_data
        bookings.append(_ns(b))

    return render(request, "registration/dashboard.html", {"bookings": bookings})


def account_overview(request):
    token = _token(request)
    if not token:
        return redirect("login")
    try:
        user = api_client.accounts_me(token)
    except Exception:
        user = None
    dealer_info = None
    if token:
        try:
            dealer_data = api_client.rentals_dealer_dashboard(token)
            dealer_info = dealer_data.get("dealer")
        except Exception:
            dealer_info = None
    return render(
        request,
        "registration/account_overview.html",
        {"user_obj": user, "dealer_form": None, "dealer_info": dealer_info},
    )


def logout_view(request):
    resp = redirect("home")
    resp.delete_cookie("auth_token")
    resp.delete_cookie("is_dealer")
    return resp
