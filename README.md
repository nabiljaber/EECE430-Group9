# EECE430-Group9

## Microservice-style local run (Docker)

We now run the site as separate containers for the main features:
- **rentals** service: home/browse/detail, bookings, dealer dashboard.
- **accounts** service: authentication and account pages.
- **nginx** reverse proxy: routes `/accounts/*` (and `/admin/`) to the accounts container, everything else to rentals.
- **db**: Postgres.

### 1) Create your environment file
```bash
cp .env.example .env
# then edit .env and set SECRET_KEY and any DB credentials you prefer
```

### 2) Build and start
```bash
docker-compose up --build
```
The site will be available at http://localhost:8000 (nginx).

### 3) Database
Migrations run automatically in the `rentals` service on startup. The database is Postgres (container `db`).

### 4) Static & media
Static files are collected to `staticfiles/` (shared volume) and served by nginx. Media uploads are stored in the `media/` volume and shared across services.

### 5) Useful commands
- Stop stack: `docker-compose down`
- Rebuild after code changes: `docker-compose up --build`
- Apply migrations manually (if needed): `docker-compose run --rm rentals python manage.py migrate`

## Microservice refactor in progress
- API contract documented at `docs/api-contract.md`.
- New services (Django + DRF): `services/accounts_service/` and `services/rentals_service/` with JWT auth and rentals logic moved to APIs.
- Gateway (original project) now begins consuming the services via HTTP and JWT cookies for login/signup, browse, detail, bookings, favorites.
- Docker stack updated to run gateway + accounts_service + rentals_service + nginx + separate Postgres DBs.
