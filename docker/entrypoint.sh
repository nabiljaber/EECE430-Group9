#!/bin/sh
set -e

echo "[$(date +"%H:%M:%S")] Starting entrypoint for ${APP_ROLE:-app}"

# Wait for Postgres if configured
if [ "${DB_ENGINE:-sqlite}" = "postgres" ]; then
  echo "Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  python - <<'PY'
import os, sys, socket, time
host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
for i in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("Postgres is up.")
            sys.exit(0)
    except OSError:
        print("Postgres not ready, retrying...")
        time.sleep(1)
print("Postgres did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY
fi

# Run migrations only when asked (avoid duplicate runs across services)
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying migrations..."
  python manage.py migrate --noinput
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput --verbosity 0 || true

echo "Starting application: $*"
exec "$@"

