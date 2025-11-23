import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return str(os.getenv(name, str(default))).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("ACCOUNTS_SECRET_KEY", "dev-accounts-secret-key")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
# Also allow the internal service hostnames
ALLOWED_HOSTS += ["accounts_service", "accounts_service:8000", "localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "accounts_api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "accounts_service.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "accounts_service.wsgi.application"

if os.getenv("DB_ENGINE", "postgres") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "accounts"),
            "USER": os.getenv("POSTGRES_USER", "accounts"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "accounts"),
            "HOST": os.getenv("POSTGRES_HOST", "db_accounts"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Simplified password validation for service-to-service signup
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 9}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
}

SIMPLE_JWT = {
    "ALGORITHM": os.getenv("ACCOUNTS_JWT_ALG", "HS256"),
    "SIGNING_KEY": os.getenv("ACCOUNTS_JWT_SECRET", SECRET_KEY),
    "VERIFYING_KEY": os.getenv("ACCOUNTS_JWT_PUBLIC", None),
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=int(os.getenv("ACCESS_TOKEN_LIFETIME", "3600"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(seconds=int(os.getenv("REFRESH_TOKEN_LIFETIME", "604800"))),
}
