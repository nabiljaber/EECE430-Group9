# Microservice API Contract (Accounts / Rentals)

Goal: keep the current UX/URLs the same while moving logic/data behind two services:
- **Accounts Service**: auth and user profile (first/last/email, username). Issues JWT for cross-service identity.
- **Rentals Service**: cars, dealers, bookings, favorites, media.
- **Gateway**: serves HTML templates; replaces ORM calls with HTTP calls to these services; forwards the user's JWT in `Authorization: Bearer <token>`.

## Auth model
- JWT HS256 (shared secret between services) or RS256 (Accounts publishes public key); initial implementation can use HS256 via `ACCOUNTS_JWT_SECRET`.
- Claims: `sub` (user id, UUID or int), `username`, `email`, `is_dealer` (bool), `exp`, `iat`.
- Gateway sets `auth_token` cookie (HttpOnly, Secure) and includes `Authorization` when calling Rentals.

## Accounts Service
Base path: `/api/accounts`

### Endpoints
- `POST /api/auth/signup` → body: `{username, password, email, first_name, last_name}` → returns `{user, token}`.
- `POST /api/auth/login` → body: `{username, password}` → `{user, token}`.
- `POST /api/auth/logout` → clears/invalidates (stateless; gateway just drops cookie).
- `POST /api/auth/refresh` → body: `{refresh}` → `{token}` (optional if using access/refresh).
- `GET /api/auth/me` → returns `{user}` (requires Bearer).
- `POST /api/auth/password-reset` → body: `{email}`; sends email (dev: console).
- `POST /api/auth/password-reset/confirm` → body: `{uid, token, new_password}`.
- `PATCH /api/users/me` → body: `{first_name?, last_name?, email?}` → `{user}`.

### User shape
```json
{
  "id": 123,
  "username": "alice",
  "email": "a@example.com",
  "first_name": "Alice",
  "last_name": "Doe",
  "is_dealer": false
}
```

## Rentals Service
Base path: `/api/rentals`
All endpoints require Bearer unless noted (public browse/detail).

### Cars (public)
- `GET /api/cars` (public)
  - Query: `q`, `make`, `dealer`, `type`, `min_price`, `max_price`, `sort` (newest|price_low|price_high), `page`.
  - Response: `{"results": [...cars], "count": n, "page": 1, "pages": N}`.
- `GET /api/cars/{id}` (public)
  - Response includes car fields, dealer, `primary_image`, `images`, and availability calendar:
    - `current_booking`, `next_booking`, `calendar_months` (12 months, weeks/days with booked flags), `upcoming_bookings` (5).

Car shape (summary):
```json
{
  "id": 10,
  "title": "Civic",
  "car_type": "sedan",
  "price_per_day": "55.00",
  "currency": "USD",
  "available": true,
  "year": 2020,
  "make": "Honda",
  "model": "Civic",
  "color": "Blue",
  "transmission": "AUTO",
  "seats": 5,
  "doors": 4,
  "mileage_km": 25000,
  "location_city": "Beirut",
  "location_country": "LB",
  "dealer": {"id": 2, "name": "Ace Motors", "phone": "...", "email": "..."},
  "primary_image": "/media/cars/primary.jpg"
}
```

### Booking (customer)
- `POST /api/bookings` → body: `{car_id, start_date, end_date, insurance_selected}` → validates overlap/past dates, blocks dealers booking; returns booking with `total_price`, `insurance_fee`.
- `GET /api/bookings/mine` → list bookings for current user (dashboard).

### Favorites
- `POST /api/favorites/toggle` → body: `{car_id}` → returns `{is_favorite: bool}`.
- `GET /api/favorites` → list current user favorites with car summary.

### Dealer onboarding
- `POST /api/dealers/apply` → body: `{username, password, email, first_name?, last_name?, dealership_name, dealership_email, dealership_phone?}`
  - Creates user (via Accounts) or accepts existing JWT? Easiest: requires logged-in user; creates dealer profile for `sub`.
  - Returns dealer profile `{id, name, email, phone, active}` and sets `is_dealer=true` in JWT claims for subsequent logins.

### Dealer inventory & pricing
- `GET /api/dealer/cars` (dealer only) → list cars the dealer owns with metrics summary.
- `POST /api/dealer/cars` → create car (body mirrors DealerCarForm); optional multipart `image` for primary photo.
- `PATCH /api/dealer/cars/{id}` → update car fields; optional `image` adds CarImage (primary if none).
- `DELETE /api/dealer/cars/{id}` → delete car.
- `POST /api/dealer/cars/{id}/price` → body: `{price_per_day}`.
- `GET /api/dealer/dashboard` → aggregates: bookings_count (current month), revenue, pending, per-car `confirmed_bookings`, `confirmed_revenue`, availability snippets (`current_booking`, `next_booking`, `upcoming_bookings` limited to 4).

### Dealer bookings
- `GET /api/dealer/cars/{id}/bookings` → list bookings for that car + calendar weeks (current month) + upcoming trips.
- `POST /api/dealer/bookings/{booking_id}/status` → body: `{action: "confirm"|"cancel"|"reject"}`.

### Media
- `POST /api/cars/{id}/images` (dealer) multipart upload → creates CarImage; payload field `is_primary` optional.
- `GET /api/cars/{id}/images` → list images.
Storage stays local/S3 bucket but URLs returned for gateway rendering.

## Gateway expectations
- Keeps current URLs and templates.
- For each view, replace ORM with API calls:
  - Home: `GET /api/cars?sort=newest&limit=8`.
  - Browse: `GET /api/cars` with filters/sort/pagination.
  - Detail: `GET /api/cars/{id}`; POST booking → `POST /api/bookings`; favorites → toggle endpoint.
  - Account dashboard: `GET /api/bookings/mine`.
  - Account overview: `GET /api/auth/me` + dealer profile (if any from rentals) and `PATCH /api/users/me` (Accounts) plus dealer update endpoint (Rentals).
  - Dealer dashboard: `GET /api/dealer/dashboard`.
  - Dealer car CRUD/price: corresponding dealer endpoints.
  - Dealer car bookings page: `GET /api/dealer/cars/{id}/bookings`, actions via status endpoint.
- Auth: Gateway validates/refreshes JWT via Accounts, forwards Bearer to Rentals.

## Error/validation
- Standard JSON errors: `{"detail": "...", "fields": {"field": ["msg", ...]}}`, HTTP 400 for validation, 401 for auth, 403 for dealer-only.
- Booking overlap/past-date errors surfaced via 400 with message used in template alerts.

