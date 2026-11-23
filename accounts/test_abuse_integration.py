"""Kayıt (bot tuzağı ve hız sınırı), giriş ve admin girişi koruması."""

import re
import time
from datetime import timedelta

import pytest
from django.core import signing
from django.test import Client
from django.urls import reverse

from abuse.limits import Limit

from .forms import (
    FORM_EXPIRED_MESSAGE,
    FORM_TOKEN_SALT,
    RegisterForm,
    form_token_is_valid,
    make_form_token,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Guclu-Parola-123"
REGISTER_URL = reverse("accounts:register")
LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
FEED_URL = reverse("polls:feed")
ADMIN_LOGIN_URL = "/admin/login/"
EMAIL = "uye@example.com"
MINUTE = timedelta(minutes=1)
QUARTER_HOUR = timedelta(minutes=15)
HOUR = timedelta(hours=1)


def register_data(username="ali", email="ali@example.com", **overrides):
    data = {
        "username": username,
        "email": email,
        "password1": PASSWORD,
        "password2": PASSWORD,
        "hp_alan": "",
        "form_ts": make_form_token(time.time() - 10),
    }
    data.update(overrides)
    return data


def is_logged_in(client) -> bool:
    return "_auth_user_id" in client.session


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(email=EMAIL, username="uye", password=PASSWORD)


# ---------- Bot tuzağı: kayıt formu ----------


def test_valid_registration_passes_the_trap(client, django_user_model):
    response = client.post(REGISTER_URL, register_data())

    assert response.status_code == 302
    assert django_user_model.objects.filter(username="ali").exists()


# Belirteçler testin İÇİNDE üretilir (lambda): parametre listesi test toplanırken değerlendirilir,
# "şimdi açılmış form" o zaman damgalanırsa test çalışana kadar yeterince yaşlanmış olurdu.
BOT_LIKE = {
    "tuzak-dolu": lambda: {"hp_alan": "http://spam.example"},
    "belirtec-yok": lambda: {"form_ts": ""},
    "imzasiz": lambda: {"form_ts": "uydurma"},
    "cok-hizli": lambda: {"form_ts": make_form_token(time.time())},  # form şimdi açılmış
    "cok-eski": lambda: {"form_ts": make_form_token(time.time() - 3 * 3600)},  # 2 saat sınırı
    "baska-tuz": lambda: {
        "form_ts": signing.Signer(salt="baska-tuz").sign(str(int(time.time()) - 10))
    },
}


@pytest.mark.parametrize("name", BOT_LIKE)
def test_bot_like_submissions_are_rejected(client, django_user_model, name):
    response = client.post(REGISTER_URL, register_data(**BOT_LIKE[name]()))

    assert response.status_code == 200
    assert FORM_EXPIRED_MESSAGE in response.content.decode()
    assert not django_user_model.objects.exists()
    assert not is_logged_in(client)


def test_tampered_token_is_rejected(client, django_user_model):
    token = make_form_token(time.time() - 10)
    response = client.post(REGISTER_URL, register_data(form_ts=token + "x"))

    assert response.status_code == 200
    assert not django_user_model.objects.exists()


def test_the_error_does_not_reveal_which_check_failed(client):
    bodies = [
        client.post(REGISTER_URL, register_data(hp_alan="x")).content.decode(),
        client.post(REGISTER_URL, register_data(form_ts="")).content.decode(),
    ]

    for body in bodies:
        assert FORM_EXPIRED_MESSAGE in body
        for hint in ("tuzak", "bot", "honeypot", "hp_alan değer", "çok hızlı"):
            assert hint not in body.lower().replace('name="hp_alan"', "")


def test_register_page_has_the_hidden_trap_and_a_fresh_token(client):
    body = client.get(REGISTER_URL).content.decode()
    token = re.search(r'name="form_ts" value="([^"]+)"', body).group(1)

    assert 'class="hp-field" aria-hidden="true" inert' in body
    assert 'name="hp_alan"' in body
    assert 'tabindex="-1"' in body
    assert signing.Signer(salt=FORM_TOKEN_SALT).unsign(token).isdigit()
    assert not form_token_is_valid(token)  # şimdi açılan form hemen gönderilirse çok hızlı sayılır


def test_a_rejected_form_comes_back_with_a_fresh_token(client, django_user_model, settings):
    stale = register_data(form_ts=make_form_token(time.time() - 3 * 3600))
    response = client.post(REGISTER_URL, stale)
    fresh = re.search(r'name="form_ts" value="([^"]+)"', response.content.decode()).group(1)

    assert fresh != stale["form_ts"]
    settings.REGISTER_MIN_FILL_SECONDS = 0  # insan birkaç saniye bekler; testte beklemeyiz
    retry = client.post(REGISTER_URL, register_data(form_ts=fresh))

    assert retry.status_code == 302  # kullanıcı eski belirteçle takılıp kalmaz
    assert django_user_model.objects.filter(username="ali").exists()


def test_a_valid_token_survives_a_validation_error(client, django_user_model):
    token = make_form_token(time.time() - 10)
    response = client.post(REGISTER_URL, register_data(form_ts=token, password2="Baska-Parola-1"))
    returned = re.search(r'name="form_ts" value="([^"]+)"', response.content.decode()).group(1)

    assert response.status_code == 200
    assert returned == token  # geçerli belirteç korunur: süre sıfırlanmaz


def test_token_age_limits_come_from_settings(client, settings, django_user_model):
    settings.REGISTER_MIN_FILL_SECONDS = 30
    young = register_data(form_ts=make_form_token(time.time() - 10))

    assert client.post(REGISTER_URL, young).status_code == 200
    assert not django_user_model.objects.exists()


# ---------- Kayıt: hız sınırı ----------


def test_registration_attempts_are_limited_per_ip(monkeypatch, django_user_model):
    monkeypatch.setattr("accounts.views.REGISTER", Limit("register", ((2, HOUR),)))

    # Her kayıt yeni oturum (Client) açar: biri giriş yapınca /kayit/ yönlendirir.
    codes = [
        Client().post(REGISTER_URL, register_data(f"kisi{i}", f"k{i}@example.com")).status_code
        for i in range(3)
    ]

    assert codes == [302, 302, 429]
    assert django_user_model.objects.count() == 2


def test_failed_registration_attempts_count_too(client, monkeypatch):
    monkeypatch.setattr("accounts.views.REGISTER", Limit("register", ((2, HOUR),)))

    codes = [client.post(REGISTER_URL, register_data(hp_alan="bot")).status_code for _ in range(3)]

    assert codes == [200, 200, 429]  # bot denemeleri de sayılır


def test_register_limit_page_is_branded(client, monkeypatch):
    monkeypatch.setattr("accounts.views.REGISTER", Limit("register", ((1, HOUR),)))
    client.post(REGISTER_URL, register_data(hp_alan="bot"))

    response = client.post(REGISTER_URL, register_data())
    body = response.content.decode()

    assert response.status_code == 429
    assert "Biraz yavaşla" in body
    assert "Bu ağdan çok fazla kayıt denemesi yapıldı." in body
    assert int(response["Retry-After"]) >= 1


def test_viewing_the_register_page_is_not_limited(client, monkeypatch):
    monkeypatch.setattr("accounts.views.REGISTER", Limit("register", ((1, HOUR),)))

    assert [client.get(REGISTER_URL).status_code for _ in range(5)] == [200] * 5


# ---------- Giriş: başarısız denemeler ----------


def fail_login(client, email=EMAIL, password="yanlis-parola", url=LOGIN_URL):
    return client.post(url, {"username": email, "password": password, "next": "/"})


def limit_failures(monkeypatch, maximum):
    monkeypatch.setattr(
        "abuse.decorators.LOGIN_FAILURE_EMAIL",
        Limit("login_fail_email", ((maximum, QUARTER_HOUR),)),
    )


def test_repeated_failures_lock_the_email_even_for_the_right_password(client, member, monkeypatch):
    limit_failures(monkeypatch, 3)
    assert [fail_login(client).status_code for _ in range(3)] == [200, 200, 200]

    locked = client.post(LOGIN_URL, {"username": EMAIL, "password": PASSWORD})

    assert locked.status_code == 429
    assert not is_logged_in(client)  # kaba kuvvet doğru parolayı bulsa bile içeri giremez
    assert int(locked["Retry-After"]) >= 1


def test_lock_page_is_branded(client, member, monkeypatch):
    limit_failures(monkeypatch, 1)
    fail_login(client)

    body = fail_login(client).content.decode()

    assert "Biraz yavaşla" in body
    assert "Çok fazla başarısız giriş denemesi yapıldı." in body


def test_unknown_emails_are_locked_exactly_like_known_ones(client, member, monkeypatch):
    limit_failures(monkeypatch, 2)
    for email in (EMAIL, "yok@example.com"):
        for _ in range(2):
            fail_login(client, email=email)

    known = fail_login(client, email=EMAIL)
    unknown = fail_login(client, email="yok@example.com")

    assert known.status_code == unknown.status_code == 429
    assert known.content == unknown.content  # hesabın var olup olmadığı sızmaz


def test_lock_is_per_email_not_global(client, member, monkeypatch):
    limit_failures(monkeypatch, 2)
    for _ in range(2):
        fail_login(client)

    assert fail_login(client, email="baska@example.com").status_code == 200
    assert fail_login(client).status_code == 429


def test_email_case_does_not_bypass_the_lock(client, member, monkeypatch):
    limit_failures(monkeypatch, 2)
    for email in ("UYE@Example.com", " uye@example.com "):
        fail_login(client, email=email)

    assert fail_login(client, email="Uye@EXAMPLE.com").status_code == 429


def test_successful_logins_do_not_count_as_failures(client, member, monkeypatch):
    limit_failures(monkeypatch, 2)

    for _ in range(5):
        response = client.post(LOGIN_URL, {"username": EMAIL, "password": PASSWORD})
        assert response.status_code == 302
        client.post(LOGOUT_URL)


def test_failures_below_the_limit_do_not_lock(client, member, monkeypatch):
    limit_failures(monkeypatch, 3)
    fail_login(client)
    fail_login(client)

    assert client.post(LOGIN_URL, {"username": EMAIL, "password": PASSWORD}).status_code == 302


def test_empty_email_failures_are_not_attributed_to_anyone(client, monkeypatch):
    limit_failures(monkeypatch, 1)

    codes = [fail_login(client, email="").status_code for _ in range(4)]

    assert codes == [200] * 4  # özne yoksa sayılmaz (herkes tek kovaya düşmez)


# ---------- Giriş: IP başına ----------


def test_login_attempts_are_limited_per_ip(client, member, monkeypatch):
    monkeypatch.setattr("abuse.decorators.LOGIN_IP", Limit("login_ip", ((2, MINUTE),)))

    codes = [fail_login(client, email=f"k{i}@example.com").status_code for i in range(3)]

    assert codes == [200, 200, 429]  # farklı e-postalar bile aynı IP'den sayılır


def test_ip_limit_blocks_even_correct_credentials(client, member, monkeypatch):
    monkeypatch.setattr("abuse.decorators.LOGIN_IP", Limit("login_ip", ((1, MINUTE),)))
    fail_login(client, email="baska@example.com")

    response = client.post(LOGIN_URL, {"username": EMAIL, "password": PASSWORD})

    assert response.status_code == 429
    assert "Bu ağdan çok fazla giriş denemesi yapıldı." in response.content.decode()


def test_viewing_the_login_page_is_not_limited(client, monkeypatch):
    monkeypatch.setattr("abuse.decorators.LOGIN_IP", Limit("login_ip", ((1, MINUTE),)))

    assert [client.get(LOGIN_URL).status_code for _ in range(5)] == [200] * 5


# ---------- Admin girişi ----------


def test_admin_login_page_still_works(client):
    assert client.get(ADMIN_LOGIN_URL).status_code == 200


def test_admin_login_failures_are_locked(client, member, monkeypatch):
    limit_failures(monkeypatch, 2)

    codes = [fail_login(client, url=ADMIN_LOGIN_URL).status_code for _ in range(2)]
    locked = fail_login(client, url=ADMIN_LOGIN_URL)

    assert codes == [200, 200]
    assert locked.status_code == 429  # /admin/ girişi de kaba kuvvete açık değil


def test_admin_login_ip_limit(client, member, monkeypatch):
    monkeypatch.setattr("abuse.decorators.LOGIN_IP", Limit("login_ip", ((1, MINUTE),)))
    fail_login(client, url=ADMIN_LOGIN_URL)

    assert fail_login(client, url=ADMIN_LOGIN_URL).status_code == 429


def test_superuser_can_still_log_in_to_admin(client, django_user_model):
    django_user_model.objects.create_superuser(
        email="patron@example.com", username="patron", password=PASSWORD
    )

    response = client.post(
        ADMIN_LOGIN_URL, {"username": "patron@example.com", "password": PASSWORD, "next": "/admin/"}
    )

    assert response.status_code == 302
    assert is_logged_in(client)


def test_site_and_admin_logins_share_the_email_lock(client, member, monkeypatch):
    limit_failures(monkeypatch, 2)
    fail_login(client)
    fail_login(client, url=ADMIN_LOGIN_URL)

    assert fail_login(client).status_code == 429
    assert fail_login(client, url=ADMIN_LOGIN_URL).status_code == 429


def test_emergency_switch_disables_login_protection(client, member, settings, monkeypatch):
    settings.RATE_LIMITS_ENABLED = False
    limit_failures(monkeypatch, 1)

    assert [fail_login(client).status_code for _ in range(4)] == [200] * 4


# ---------- İncelemeden gelen düzeltmeler ----------

FULLWIDTH_EMAIL = "ｕｙｅ@ｅｘａｍｐｌｅ.ｃｏｍ"  # Django girişte NFKC ile "uye@example.com" yapar


def test_django_really_treats_the_fullwidth_email_as_the_same_account(client, member):
    # Atlatma varsayımının dayanağı: bu varyantla aynı hesaba giriş yapılabiliyor.
    response = client.post(LOGIN_URL, {"username": FULLWIDTH_EMAIL, "password": PASSWORD})

    assert response.status_code == 302
    assert is_logged_in(client)


def test_unicode_email_variants_share_one_lock(client, member, monkeypatch):
    limit_failures(monkeypatch, 3)

    # Her varyant ayrı kova olsaydı 10 başarısız deneme sınırı fiilen olmazdı.
    for email in (FULLWIDTH_EMAIL, "UYE@example.com", " uye@example.com"):
        fail_login(client, email=email)

    assert fail_login(client, email=EMAIL).status_code == 429
    assert fail_login(client, email=FULLWIDTH_EMAIL).status_code == 429


@pytest.mark.parametrize("email", ["x" * 1000 + "@example.com", "a\x00b@example.com", "💥" * 300])
def test_odd_emails_do_not_crash_the_protected_login(client, email):
    assert fail_login(client, email=email).status_code == 200  # form reddeder, 500 değil


def test_login_ip_hourly_window_blocks_slow_password_spraying(client, member, monkeypatch):
    monkeypatch.setattr("abuse.decorators.LOGIN_IP", Limit("login_ip", ((100, MINUTE), (2, HOUR))))

    codes = [fail_login(client, email=f"k{i}@example.com").status_code for i in range(3)]

    assert codes == [200, 200, 429]


# ---------- Bot tuzağı: belirteç denetimi zamanı ----------


def test_missing_token_is_rejected_even_if_the_minimum_age_is_zero(
    client, settings, django_user_model
):
    settings.REGISTER_MIN_FILL_SECONDS = 0

    response = client.post(REGISTER_URL, register_data(form_ts=""))

    assert response.status_code == 200
    assert not django_user_model.objects.exists()


def test_slow_field_validation_cannot_make_a_missing_token_valid(monkeypatch):
    form = RegisterForm(register_data(form_ts=""))  # kurulurken belirteç geçersiz sayılır
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + 30)  # alan temizliği 30 sn sürdü

    assert not form.is_valid()
    assert FORM_EXPIRED_MESSAGE in form.non_field_errors()


def test_a_valid_token_stays_valid_while_the_fields_are_being_cleaned(monkeypatch):
    form = RegisterForm(register_data())
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + 30)

    assert form.is_valid()  # denetim kurulurken yapıldı, sonradan yaşlanmak onu bozmaz
