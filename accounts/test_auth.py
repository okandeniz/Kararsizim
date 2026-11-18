import pytest
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from .forms import RegisterForm

pytestmark = pytest.mark.django_db

PASSWORD = "Guclu-Parola-123"
REGISTER_URL = reverse("accounts:register")
LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
FEED_URL = reverse("polls:feed")


def register_data(**overrides):
    data = {
        "username": "ali",
        "email": "ali@example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password=PASSWORD
    )


def is_logged_in(client) -> bool:
    return "_auth_user_id" in client.session


# ---------- Kayıt ----------


def test_register_page_renders(client):
    response = client.get(REGISTER_URL)
    assert response.status_code == 200
    body = response.content.decode()
    assert "Anketlerde bu ad görünecek." in body
    assert "E-postan kimseye gösterilmez." in body
    assert "csrfmiddlewaretoken" in body


def test_register_success_logs_in_and_redirects_home(client, django_user_model):
    response = client.post(REGISTER_URL, register_data(), follow=True)

    assert response.redirect_chain == [(FEED_URL, 302)]
    assert is_logged_in(client)
    assert django_user_model.objects.filter(username="ali").exists()
    assert "Hoş geldin @ali!" in response.content.decode()


def test_register_lowercases_email(client, django_user_model):
    client.post(REGISTER_URL, register_data(email="Ali@Example.COM"))
    assert django_user_model.objects.get(username="ali").email == "ali@example.com"


def test_register_respects_safe_next(client):
    response = client.post(REGISTER_URL, register_data(next="/anket/yeni/"))
    assert response.status_code == 302
    assert response.url == "/anket/yeni/"


@pytest.mark.parametrize(
    "unsafe", ["https://evil.example/", "//evil.example/", "javascript:alert(1)"]
)
def test_register_ignores_unsafe_next(client, unsafe):
    response = client.post(REGISTER_URL, register_data(next=unsafe))
    assert response.status_code == 302
    assert response.url == FEED_URL


def test_register_get_next_is_kept_in_form_and_login_link(client):
    body = client.get(REGISTER_URL, {"next": "/anket/yeni/"}).content.decode()
    assert 'name="next" value="/anket/yeni/"' in body
    assert f"{LOGIN_URL}?next=/anket/yeni/" in body


@pytest.mark.parametrize("email", ["uye@example.com", "UYE@Example.com"])
def test_register_rejects_duplicate_email_any_case(client, member, django_user_model, email):
    response = client.post(REGISTER_URL, register_data(email=email))

    assert response.status_code == 200
    assert "Bu e-posta ile zaten bir hesap var." in response.content.decode()
    assert not is_logged_in(client)
    assert django_user_model.objects.count() == 1


@pytest.mark.parametrize("username", ["uye", "Uye", "UYE"])
def test_register_rejects_duplicate_username_any_case(client, member, django_user_model, username):
    response = client.post(REGISTER_URL, register_data(username=username))

    assert response.status_code == 200
    assert "Bu kullanıcı adı alınmış." in response.content.decode()
    assert django_user_model.objects.count() == 1


@pytest.mark.parametrize(
    "username",
    ["ab", "a" * 21, "ali veli", "ali-veli", "çağrı", "admin", "Kararsizim"],
)
def test_register_rejects_invalid_username(client, django_user_model, username):
    response = client.post(REGISTER_URL, register_data(username=username))

    assert response.status_code == 200
    assert response.context["form"].errors.get("username")
    assert not django_user_model.objects.exists()


def test_register_rejects_password_mismatch(client, django_user_model):
    response = client.post(REGISTER_URL, register_data(password2="Baska-Parola-456"))

    assert response.status_code == 200
    assert response.context["form"].errors.get("password2")
    assert not django_user_model.objects.exists()


def test_register_rejects_weak_password(client, django_user_model):
    response = client.post(REGISTER_URL, register_data(password1="12345678", password2="12345678"))

    assert response.status_code == 200
    assert response.context["form"].errors.get("password2")
    assert not django_user_model.objects.exists()


def test_register_rejects_invalid_email(client, django_user_model):
    response = client.post(REGISTER_URL, register_data(email="bu-bir-eposta-degil"))

    assert response.status_code == 200
    assert response.context["form"].errors.get("email")
    assert not django_user_model.objects.exists()


# ---------- Giriş ----------


def test_login_page_renders(client):
    response = client.get(LOGIN_URL)
    assert response.status_code == 200
    body = response.content.decode()
    assert "E-posta" in body
    assert "Hesabın yok mu?" in body


def test_login_success(client, member):
    response = client.post(LOGIN_URL, {"username": "uye@example.com", "password": PASSWORD})

    assert response.status_code == 302
    assert response.url == FEED_URL
    assert is_logged_in(client)


def test_login_email_is_case_insensitive(client, member):
    client.post(LOGIN_URL, {"username": "UYE@Example.com", "password": PASSWORD})
    assert is_logged_in(client)


@pytest.mark.parametrize(
    ("email", "password"),
    [("uye@example.com", "yanlis-parola"), ("yok@example.com", PASSWORD)],
)
def test_login_failure_shows_generic_message(client, member, email, password):
    response = client.post(LOGIN_URL, {"username": email, "password": password})

    assert response.status_code == 200
    assert "E-posta veya parola hatalı." in response.content.decode()
    assert not is_logged_in(client)


def test_login_by_username_is_not_possible(client, member):
    client.post(LOGIN_URL, {"username": "uye", "password": PASSWORD})
    assert not is_logged_in(client)


def test_login_inactive_user_gets_same_generic_message(client, member):
    member.is_active = False
    member.save()
    response = client.post(LOGIN_URL, {"username": "uye@example.com", "password": PASSWORD})

    assert "E-posta veya parola hatalı." in response.content.decode()
    assert not is_logged_in(client)


def test_login_redirects_to_safe_next(client, member):
    response = client.post(
        LOGIN_URL, {"username": "uye@example.com", "password": PASSWORD, "next": "/anket/yeni/"}
    )
    assert response.url == "/anket/yeni/"


def test_login_ignores_unsafe_next(client, member):
    response = client.post(
        LOGIN_URL,
        {"username": "uye@example.com", "password": PASSWORD, "next": "https://evil.example/"},
    )
    assert response.url == FEED_URL


def test_login_page_keeps_next_in_register_link(client):
    body = client.get(LOGIN_URL, {"next": "/anket/yeni/"}).content.decode()
    assert 'name="next" value="/anket/yeni/"' in body
    assert f"{REGISTER_URL}?next=/anket/yeni/" in body


# ---------- Giriş yapmış kullanıcı ----------


@pytest.mark.parametrize("url", [REGISTER_URL, LOGIN_URL])
def test_authenticated_user_is_redirected_from_guest_pages(client, member, url):
    client.force_login(member)
    response = client.get(url)

    assert response.status_code == 302
    assert response.url == FEED_URL


# ---------- Çıkış ----------


def test_logout_post_logs_out(client, member):
    client.force_login(member)
    response = client.post(LOGOUT_URL)

    assert response.status_code == 302
    assert response.url == FEED_URL
    assert not is_logged_in(client)


def test_logout_get_is_not_allowed(client, member):
    client.force_login(member)
    response = client.get(LOGOUT_URL)

    assert response.status_code == 405
    assert is_logged_in(client)


def test_logout_post_requires_csrf_token(member):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(member)
    response = csrf_client.post(LOGOUT_URL)

    assert response.status_code == 403
    assert "_auth_user_id" in csrf_client.session


# ---------- Header ve gizlilik ----------


def test_header_for_guest(client):
    body = client.get(FEED_URL).content.decode()
    assert "Anket oluştur" in body
    assert f'href="{LOGIN_URL}"' in body
    assert f'href="{REGISTER_URL}"' in body
    assert LOGOUT_URL not in body


def test_header_for_member_shows_username_and_logout_form(client, member):
    client.force_login(member)
    body = client.get(FEED_URL).content.decode()

    assert "Anket oluştur" in body
    assert "@uye" in body
    assert f'action="{LOGOUT_URL}"' in body
    assert "csrfmiddlewaretoken" in body
    assert f'href="{LOGIN_URL}"' not in body
    assert f'href="{REGISTER_URL}"' not in body


def test_email_is_never_rendered_for_logged_in_user(client, member):
    client.force_login(member)
    # Herkese açık sayfalar (admin hariç: orası yalnızca süper kullanıcılar içindir).
    for url in (FEED_URL, REGISTER_URL, LOGIN_URL):
        assert member.email not in client.get(url, follow=True).content.decode()


def test_registration_flow_does_not_leak_email(client):
    response = client.post(REGISTER_URL, register_data(), follow=True)
    assert "ali@example.com" not in response.content.decode()


# ---------- İnceleme sonrası eklenen senaryolar ----------


def test_register_handles_integrity_error_race(client, django_user_model, monkeypatch):
    # Form denetimini geçen ama DB kısıtına çarpan eşzamanlı kayıt: 500 değil, form hatası.
    def raise_integrity_error(self, commit=True):
        raise IntegrityError("duplicate key")

    monkeypatch.setattr(RegisterForm, "save", raise_integrity_error)
    response = client.post(REGISTER_URL, register_data())

    assert response.status_code == 200
    assert "Bu e-posta veya kullanıcı adı alınmış." in response.content.decode()
    assert not is_logged_in(client)
    assert not django_user_model.objects.exists()


@pytest.mark.parametrize("url", [REGISTER_URL, LOGIN_URL])
def test_authenticated_post_to_guest_pages_redirects_home(client, member, url):
    client.force_login(member)
    response = client.post(url, register_data())

    assert response.status_code == 302
    assert response.url == FEED_URL


def test_authenticated_user_with_self_referencing_next_does_not_crash(client, member):
    client.force_login(member)
    response = client.get(LOGIN_URL, {"next": LOGIN_URL})

    assert response.status_code == 302
    assert response.url == FEED_URL


@pytest.mark.parametrize("url", [REGISTER_URL, LOGIN_URL])
def test_guest_forms_enforce_csrf(url):
    csrf_client = Client(enforce_csrf_checks=True)
    response = csrf_client.post(url, register_data())

    assert response.status_code == 403
