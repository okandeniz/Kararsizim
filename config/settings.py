"""
kararsızım Django ayarları.

Tüm ortama bağlı değerler ortam değişkenlerinden okunur (yerelde .env dosyasından).
Ayrıntılar için: .env.example
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# .env dosyası yoksa sorun çıkmaz (production'da değişkenler platformdan gelir)
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


DEBUG = env_bool("DEBUG", default=False)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    # Vercel'de VERCEL değişkeni otomatik tanımlıdır; orada anahtarsız çalışmayı engelle.
    if os.environ.get("VERCEL"):
        raise ImproperlyConfigured("SECRET_KEY ortam değişkeni tanımlı olmalı.")
    SECRET_KEY = "django-insecure-yalnizca-yerel-gelistirme-icin"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "polls",
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


# Veritabanı: DATABASE_URL varsa (Supabase Postgres) onu, yoksa yerel SQLite'ı kullan.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    try:
        DATABASES = {
            "default": dj_database_url.parse(DATABASE_URL, conn_max_age=0, ssl_require=True),
        }
    except (dj_database_url.ParseError, dj_database_url.UnknownSchemeError):
        # Hata metni bilerek DATABASE_URL'i içermez (parola log'a sızmasın).
        raise ImproperlyConfigured(
            "DATABASE_URL geçerli bir bağlantı adresi değil. Kontrol et: adres postgresql:// ile "
            "başlamalı; [ ] < > tırnak ve boşluk olmamalı (Supabase'deki [YOUR-PASSWORD] "
            "köşeli parantezleriyle birlikte parolayla değiştirilmeli); parolada / # ? : @ % gibi "
            "özel karakterler varsa URL kodlaması gerekir (%2F %23 %3F %3A %40 %25); port bir "
            "sayı olmalı. Yalnızca yerelde SQLite kullanmak için DATABASE_URL satırını boş bırak."
        ) from None
    # Supabase transaction pooler (port 6543) server-side cursor'ları ve hazırlanmış ifadeleri
    # (prepared statements) desteklemez. psycopg3 varsayılan olarak aynı sorgu 5 kez
    # çalışınca otomatik hazırlar; bu, canlıda rastgele hatalara yol açar, o yüzden kapatılır.
    if str(DATABASES["default"].get("PORT")) == "6543":
        DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
        DATABASES["default"].setdefault("OPTIONS", {})["prepare_threshold"] = None
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "polls:feed"
LOGOUT_REDIRECT_URL = "polls:feed"


LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Production (DEBUG=False) güvenlik ayarları
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Vercel HTTPS'i zaten zorunlu tutuyor; yönlendirme döngüsü olmasın.
    SECURE_SSL_REDIRECT = False


# Yerelde e-postalar konsola yazılır. Production'da bilerek tanımlı değil: Django 6.1'in
# `check --deploy` kontrolü DEBUG=False iken konsol backend'ini hata sayar (mail.E001).
# Şu an e-posta gönderen bir özellik yok; parola sıfırlama (Faz 11) için gerçek servis gerekecek.
if DEBUG:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.console.EmailBackend",
        },
    }
