"""
Django settings for ajerlo project.
"""

from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Dev basics ---
SECRET_KEY = 'django-insecure-^5k7+xu3ck#6!v)r23me4y2n@nm30ivrm8h!q4myvgy(lj(40g'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# --- Branding ---
SITE_NAME = "Ajerlo Rentals"
SITE_TAGLINE = "Book cars with confidence"

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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {'timeout':20},
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
