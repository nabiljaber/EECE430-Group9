FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# System dependencies
#RUN apt-get update && \
 #   apt-get install -y --no-install-recommends build-essential curl && \
  #  rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create static folder
RUN mkdir -p /app/static /app/media

# Collect static files
RUN python manage.py collectstatic --noinput

# Permissions
RUN chmod +x docker/entrypoint.sh

ENV DJANGO_SETTINGS_MODULE=ajerlo.settings
ENV APP_ROLE=app

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "ajerlo.wsgi:application", "--bind", "0.0.0.0:8000"]
