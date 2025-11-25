import os
import requests


ACCOUNTS_API = os.getenv("ACCOUNTS_API_BASE", "http://accounts-service:8001/api")
RENTALS_API = os.getenv("RENTALS_API_BASE", "http://rentals-service:8002/api/rentals")




def _headers(token=None):
    h = {"Host": "localhost"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def accounts_me(token):
    r = requests.get(f"{ACCOUNTS_API}/auth/me/", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()["user"]


def accounts_login(username, password):
    r = requests.post(
        f"{ACCOUNTS_API}/auth/login/",
        json={"username": username, "password": password},
        timeout=10,
        headers=_headers(),
    )
    try:
        data = r.json()
    except Exception:
        data = None
    if r.status_code != 200:
        return None, data or {"detail": f"Login failed ({r.status_code})"}
    return data, None


def accounts_signup(payload):
    r = requests.post(f"{ACCOUNTS_API}/auth/signup/", json=payload, timeout=10, headers=_headers())
    try:
        data = r.json()
    except Exception:
        data = None
    if r.status_code not in (200, 201):
        # prefer text detail if JSON missing
        detail = None
        if isinstance(data, dict) and "detail" in data:
            detail = data["detail"]
        if not detail:
            detail = r.text or f"Signup failed ({r.status_code})"
        return None, {"detail": detail}
    return data, None


def rentals_list(params=None, token=None):
    r = requests.get(f"{RENTALS_API}/cars/", params=params or {}, headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def rentals_detail(car_id, token=None):
    r = requests.get(f"{RENTALS_API}/cars/{car_id}/", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def rentals_booking_create(token, payload):
    r = requests.post(f"{RENTALS_API}/bookings/", json=payload, headers=_headers(token), timeout=10)
    return r


def rentals_my_bookings(token):
    r = requests.get(f"{RENTALS_API}/bookings/mine/", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()["results"]


def rentals_toggle_favorite(token, car_id):
    r = requests.post(f"{RENTALS_API}/favorites/toggle/", json={"car_id": car_id}, headers=_headers(token), timeout=10)
    return r


def rentals_favorites(token):
    r = requests.get(f"{RENTALS_API}/favorites/", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()["results"]


def rentals_dealer_apply(token, payload):
    return requests.post(f"{RENTALS_API}/dealer/apply/", json=payload, headers=_headers(token), timeout=10)


def rentals_dealer_dashboard(token):
    r = requests.get(f"{RENTALS_API}/dealer/dashboard/", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def rentals_dealer_car_list(token):
    r = requests.get(f"{RENTALS_API}/dealer/cars/", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def rentals_dealer_car_create(token, payload, files=None):
    return requests.post(f"{RENTALS_API}/dealer/cars/", headers=_headers(token), data=payload, files=files or {}, timeout=10)


def rentals_dealer_car_update(token, car_id, payload, files=None):
    return requests.patch(f"{RENTALS_API}/dealer/cars/{car_id}/", headers=_headers(token), data=payload, files=files or {}, timeout=10)


def rentals_dealer_car_delete(token, car_id):
    return requests.delete(f"{RENTALS_API}/dealer/cars/{car_id}/", headers=_headers(token), timeout=10)


def rentals_dealer_price(token, car_id, payload):
    return requests.post(f"{RENTALS_API}/dealer/cars/{car_id}/price/", headers=_headers(token), json=payload, timeout=10)


def rentals_dealer_car_bookings(token, car_id):
    r = requests.get(f"{RENTALS_API}/dealer/cars/{car_id}/bookings/", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def rentals_dealer_booking_status(token, booking_id, action):
    return requests.post(f"{RENTALS_API}/dealer/bookings/{booking_id}/status/", headers=_headers(token), json={"action": action}, timeout=10)
