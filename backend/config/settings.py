"""
Django settings for the Weather-Aware Truck Routing API.

Deploy-specific values come from environment variables, kept in backend/.env
(never committed; it is listed in .gitignore).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# The API is stateless (no users, no stored data), so the database, auth,
# sessions and admin apps are deliberately left out.
INSTALLED_APPS = [
    "planner",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES: dict = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
