"""
Django settings for ajerlo project.
"""

from pathlib import Path
import os

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    """Read env variable and interpret common truthy strings."""
    return str(os.getenv(name, str(default))).lower() in {"1", "true", "yes", "on"}


# --- Dev basics ---
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-^5k7+xu3ck#6!v)r23me4y2n@nm30ivrm8h!q4myvgy(lj(40g')
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# Optional: allow proxy/ingress domains for CSRF
_csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS")
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = _csrf_env.split(",")
else:
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost",
        "http://127.0.0.1",
    ]

# --- Branding ---
SITE_NAME = "Ajerlo Rentals"
SITE_TAGLINE = "Book cars with confidence"

# --- Service endpoints (gateway)
ACCOUNTS_API_BASE = os.getenv("ACCOUNTS_API_BASE", "http://localhost:8001/api")
RENTALS_API_BASE = os.getenv("RENTALS_API_BASE", "http://localhost:8002/api")
ACCOUNTS_JWT_SECRET = os.getenv("ACCOUNTS_JWT_SECRET", SECRET_KEY)
ACCOUNTS_JWT_ALG = os.getenv("ACCOUNTS_JWT_ALG", "HS256")

# --- Apps ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rentals',
    'accounts',
]

# --- Middleware ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ajerlo.middleware.GatewayJWTMiddleware',
]

# --- URLs / Templates ---
ROOT_URLCONF = 'ajerlo.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Branding vars available in all templates
                "ajerlo.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = 'ajerlo.wsgi.application'

# --- Database ---
if os.getenv("DB_ENGINE", "sqlite").lower() == "postgres":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'ajerlo'),
            'USER': os.getenv('POSTGRES_USER', 'ajerlo'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'ajerlo'),
            'HOST': os.getenv('POSTGRES_HOST', 'db'),
            'PORT': int(os.getenv('POSTGRES_PORT', '5432')),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 20},
        }
    }

# --- Password validation (min length = 9) ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 9}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Static files ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# --- Media uploads ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Defaults ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Auth redirects ---
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = 'login'  # named URL

# --- Email backend (dev) for password reset ---
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@ajerlo.local'
