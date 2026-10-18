"""
Django settings for the Weather-Aware Truck Routing API.

Deploy-specific values come from environment variables, kept in backend/.env
(never committed; it is listed in .gitignore).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Copies the values from backend/.env into os.environ. Variables that are
# already set (e.g. on the hosting platform) win over the file.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated variable, e.g. "a.com, b.com" -> ["a.com", "b.com"]."""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# The API is stateless (no users, no stored data), so the database, auth,
# sessions and admin apps are deliberately left out.
INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "planner",
]

MIDDLEWARE = [
    # Must come first so CORS headers are added even to error responses.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Route geometries are large JSON; gzip shrinks them by roughly 80%.
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES: dict = {}

REST_FRAMEWORK = {
    # No login: without these, DRF would try to load Django's auth app.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# Browsers only let these origins (the React app) call the API.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True

# --- Third-party services -------------------------------------------------

# Optional. When set, Mapbox is used for geocoding and routing; otherwise the
# free, key-less Photon (geocoding) and OSRM (routing) services are used.
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

# The public OSM-based services ask every client to identify itself.
HTTP_USER_AGENT = os.getenv("HTTP_USER_AGENT", "WeatherAwareTruckRouting/1.0")
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
