"""
Django settings for the Business Lead Finder project.

This configuration supports SQLite for development and PostgreSQL for
production. All security-sensitive values can be overridden through
environment variables so the same code base can ship to production without
edits.

Free APIs only:
    * Nominatim (OpenStreetMap) for geocoding locations -> coordinates.
    * Overpass API (OpenStreetMap) for fetching businesses around a point.

No paid APIs, no Google Places, no subscriptions.
"""

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean value from the environment."""
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------- #
# Core security settings
# --------------------------------------------------------------------------- #
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-3bst(3391)qbn(+zl)5)7iton6nllt@pqb5)ci$vkdbem8i8ag",
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0"
).split(",")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]


# --------------------------------------------------------------------------- #
# Application definition
# --------------------------------------------------------------------------- #
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_filters",
    # Local apps
    "leads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files efficiently in production.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# --------------------------------------------------------------------------- #
# Database
#
# By default SQLite is used (development). If POSTGRES_DB env variable is
# present, PostgreSQL is used (production ready).
# --------------------------------------------------------------------------- #
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# --------------------------------------------------------------------------- #
# Caching
#
# Local-memory cache by default. Set REDIS_URL to use Redis in production.
# Caching geocoding + Overpass responses keeps repeat searches under 5s.
# --------------------------------------------------------------------------- #
if os.environ.get("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ.get("REDIS_URL"),
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "business-lead-finder-cache",
            "TIMEOUT": 60 * 60 * 6,  # 6 hours
            "OPTIONS": {"MAX_ENTRIES": 5000},
        }
    }


# --------------------------------------------------------------------------- #
# Password validation
# --------------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --------------------------------------------------------------------------- #
# Internationalization
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------------- #
# Static files
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------------------------------- #
# Business Lead Finder — application settings
# --------------------------------------------------------------------------- #
# OpenStreetMap endpoints (all free, no key required).
NOMINATIM_URL = os.environ.get(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
OVERPASS_URL = os.environ.get(
    "OVERPASS_URL", "https://overpass-api.de/api/interpreter"
)
# A descriptive User-Agent is required by the Nominatim usage policy.
OSM_USER_AGENT = os.environ.get(
    "OSM_USER_AGENT",
    "Mozilla/5.0 (compatible; BusinessLeadFinder/1.0; +https://example.com)"
)
# Network timeouts (seconds) to keep searches snappy.
OSM_HTTP_TIMEOUT = int(os.environ.get("OSM_HTTP_TIMEOUT", "20"))
# Cache lifetime for geocoding + Overpass responses (seconds).
OSM_CACHE_TIMEOUT = int(os.environ.get("OSM_CACHE_TIMEOUT", str(60 * 60 * 6)))
# Default search radius (meters) around the geocoded location.
OSM_SEARCH_RADIUS = int(os.environ.get("OSM_SEARCH_RADIUS", "8000"))


# --------------------------------------------------------------------------- #
# Production hardening (enabled automatically when DEBUG is False)
# --------------------------------------------------------------------------- #
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"}
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "leads": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
