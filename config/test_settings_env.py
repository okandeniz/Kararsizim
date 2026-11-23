"""config/settings.py ortam değişkenlerinden doğru ayarları kuruyor mu?

Production'a özgü ayarlar yerelde SQLite ile görünmez; burada ortam değişkenleriyle taklit edilir.
Her test modülü yeniden yükler (reload); Django'nun kendi `settings` nesnesi etkilenmez.
"""

import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured

import config.settings as settings_module

HOST = "aws-0-eu-central-1.pooler.supabase.com"
SESSION_URL = f"postgresql://postgres.abcd:pw@{HOST}:5432/postgres"
TRANSACTION_URL = f"postgresql://postgres.abcd:pw@{HOST}:6543/postgres"
ENV_NAMES = (
    "DATABASE_URL",
    "SECRET_KEY",
    "VERCEL",
    "DEBUG",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "RATE_LIMITS_ENABLED",
)


@pytest.fixture
def load_settings(monkeypatch):
    # Yerelde .env olsa bile testleri etkilemesin.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)

    def load(**env):
        for name in ENV_NAMES:
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        # reload eski çalıştırmadan kalan ayarları silmez; temiz başlangıç için önce temizle.
        for name in [attr for attr in vars(settings_module) if attr.isupper()]:
            delattr(settings_module, name)
        return importlib.reload(settings_module)

    return load


def database(module):
    return module.DATABASES["default"]


# ---------- Veritabanı ----------


def test_without_database_url_uses_sqlite(load_settings):
    assert database(load_settings())["ENGINE"] == "django.db.backends.sqlite3"


def test_session_pooler_keeps_default_connection_behaviour(load_settings):
    db = database(load_settings(DATABASE_URL=SESSION_URL))

    assert db["ENGINE"] == "django.db.backends.postgresql"
    assert str(db["PORT"]) == "5432"
    assert db["CONN_MAX_AGE"] == 0
    assert db["OPTIONS"]["sslmode"] == "require"
    assert db["DISABLE_SERVER_SIDE_CURSORS"] is False
    assert "prepare_threshold" not in db["OPTIONS"]


def test_transaction_pooler_disables_cursors_and_prepared_statements(load_settings):
    # Supabase transaction modu ikisini de desteklemez; psycopg3 5. sorguda otomatik hazırlar.
    db = database(load_settings(DATABASE_URL=TRANSACTION_URL))

    assert db["DISABLE_SERVER_SIDE_CURSORS"] is True
    assert db["OPTIONS"]["prepare_threshold"] is None
    assert db["OPTIONS"]["sslmode"] == "require"  # öncekileri ezmez
    assert db["CONN_MAX_AGE"] == 0


def test_port_digits_inside_password_do_not_trigger_transaction_mode(load_settings):
    url = f"postgresql://postgres.abcd:pa6543ss@{HOST}:5432/postgres"
    db = database(load_settings(DATABASE_URL=url))

    assert db["DISABLE_SERVER_SIDE_CURSORS"] is False
    assert "prepare_threshold" not in db["OPTIONS"]


def test_blank_database_url_falls_back_to_sqlite(load_settings):
    assert database(load_settings(DATABASE_URL="  "))["ENGINE"] == "django.db.backends.sqlite3"


# ---------- Gizli anahtar ----------


def test_secret_key_is_read_from_environment(load_settings):
    assert load_settings(SECRET_KEY="gizli-anahtar").SECRET_KEY == "gizli-anahtar"


def test_missing_secret_key_falls_back_locally(load_settings):
    assert load_settings().SECRET_KEY.startswith("django-insecure")


def test_missing_secret_key_is_fatal_on_vercel(load_settings):
    with pytest.raises(ImproperlyConfigured):
        load_settings(VERCEL="1")


def test_vercel_with_secret_key_loads(load_settings):
    assert load_settings(VERCEL="1", SECRET_KEY="x").SECRET_KEY == "x"


# ---------- DEBUG, hostlar ve güvenli çerezler ----------


def test_debug_defaults_to_false(load_settings):
    assert load_settings().DEBUG is False


@pytest.mark.parametrize(("value", "expected"), [("True", True), ("1", True), ("false", False)])
def test_debug_parsing(load_settings, value, expected):
    assert load_settings(DEBUG=value).DEBUG is expected


def test_production_mode_enables_secure_cookies_and_proxy_header(load_settings):
    module = load_settings(DEBUG="False")

    assert module.SESSION_COOKIE_SECURE is True
    assert module.CSRF_COOKIE_SECURE is True
    assert module.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert module.SECURE_SSL_REDIRECT is False  # Vercel HTTPS'i zaten zorunlu tutar


def test_debug_mode_leaves_cookies_insecure_for_local_http(load_settings):
    module = load_settings(DEBUG="True")
    assert not hasattr(module, "SESSION_COOKIE_SECURE")


def test_host_and_origin_lists_are_split_and_trimmed(load_settings):
    module = load_settings(
        ALLOWED_HOSTS=".vercel.app, example.com ,",
        CSRF_TRUSTED_ORIGINS="https://*.vercel.app",
    )

    assert module.ALLOWED_HOSTS == [".vercel.app", "example.com"]
    assert module.CSRF_TRUSTED_ORIGINS == ["https://*.vercel.app"]


def test_hosts_default_to_empty_so_production_must_configure_them(load_settings):
    module = load_settings()
    assert module.ALLOWED_HOSTS == []
    assert module.CSRF_TRUSTED_ORIGINS == []


# ---------- Vercel giriş noktası ----------


def test_wsgi_entrypoint_matches_vercel_expectation(load_settings):
    # Vercel: settings.WSGI_APPLICATION + wsgi.py içinde `application`.
    module = load_settings()
    assert module.WSGI_APPLICATION == "config.wsgi.application"
    assert not hasattr(module, "ASGI_APPLICATION")  # ASGI tanımlı olsaydı Vercel onu seçerdi

    wsgi = importlib.import_module("config.wsgi")
    assert callable(wsgi.application)


# ---------- E-posta (Django 6.1 deploy kontrolü) ----------


def test_console_mailer_only_in_debug(load_settings):
    assert "console" in load_settings(DEBUG="True").MAILERS["default"]["BACKEND"]


def test_no_development_mailer_in_production(load_settings):
    # DEBUG=False iken konsol backend'i `check --deploy`'u hata ile bitirir (mail.E001).
    assert not hasattr(load_settings(DEBUG="False"), "MAILERS")


# ---------- Geçersiz DATABASE_URL (en sık yapılan hatalar) ----------

SECRET = "S3kretParola9"


@pytest.mark.parametrize(
    "url",
    [
        f"postgresql://postgres.abcd:[{SECRET}]@{HOST}:5432/postgres",  # köşeli parantez
        f"postgresql://postgres.abcd:{SECRET}/x@{HOST}:5432/postgres",  # parolada /
        f"postgresql://postgres.abcd:{SECRET}@{HOST}:PORT/postgres",  # port yer tutucusu
        f'"postgresql://postgres.abcd:{SECRET}@{HOST}:5432/postgres"',  # tırnaklı
    ],
)
def test_invalid_database_url_gives_actionable_error_without_leaking_it(load_settings, url):
    with pytest.raises(ImproperlyConfigured) as exc_info:
        load_settings(DATABASE_URL=url)

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert "[YOUR-PASSWORD]" in message  # çözümü anlatır
    assert SECRET not in message  # parola hata metnine sızmaz
    assert HOST not in message
    assert exc_info.value.__cause__ is None  # özgün hata (URL içerebilir) zincire eklenmez


# ---------- Kötüye kullanım koruması ayarları ----------


def test_proxy_ip_headers_are_trusted_only_on_vercel(load_settings):
    # Başka ortamlarda x-forwarded-for istemci tarafından sahtelenebilir.
    assert load_settings().TRUST_PROXY_IP_HEADERS is False
    assert load_settings(VERCEL="1", SECRET_KEY="x").TRUST_PROXY_IP_HEADERS is True


def test_rate_limits_are_on_by_default(load_settings):
    assert load_settings().RATE_LIMITS_ENABLED is True


@pytest.mark.parametrize(
    ("value", "expected"), [("False", False), ("0", False), ("true", True), ("1", True)]
)
def test_rate_limits_emergency_switch(load_settings, value, expected):
    assert load_settings(RATE_LIMITS_ENABLED=value).RATE_LIMITS_ENABLED is expected


def test_register_form_age_limits_are_sane(load_settings):
    module = load_settings()

    assert 0 < module.REGISTER_MIN_FILL_SECONDS < 60
    assert module.REGISTER_MAX_AGE_SECONDS > 600  # insan uzun parola seçerken yarıda kalabilir


def test_abuse_app_is_installed(load_settings):
    assert "abuse" in load_settings().INSTALLED_APPS
