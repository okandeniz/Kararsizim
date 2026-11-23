"""404, 500 ve CSRF hata sayfaları marka diliyle ve Türkçe gösterilir."""

import pytest
from django.test import Client, RequestFactory
from django.urls import reverse
from django.views.defaults import server_error

FEED = reverse("polls:feed")


def test_unknown_url_renders_branded_404(client):
    response = client.get("/yok-boyle-bir-sayfa/")
    body = response.content.decode()

    assert response.status_code == 404
    assert "Bu sayfa kararsız kalıp kaybolmuş" in body
    assert f'href="{FEED}"' in body
    assert "<title>Sayfa bulunamadı — kararsızım</title>" in body


@pytest.mark.django_db
def test_unknown_poll_renders_branded_404(client):
    response = client.get(reverse("polls:detail", kwargs={"pk": 999999}))

    assert response.status_code == 404
    assert "Bu sayfa kararsız kalıp kaybolmuş" in response.content.decode()


def test_404_has_no_technical_details(client):
    body = client.get("/yok-boyle-bir-sayfa/").content.decode()

    assert "Django" not in body
    assert "URLconf" not in body
    assert "Request URL" not in body


def test_server_error_view_renders_branded_page():
    # Django 500 şablonunu request ve context olmadan çizer; base.html buna dayanıklı olmalı.
    response = server_error(RequestFactory().get("/"))
    body = response.content.decode()

    assert response.status_code == 500
    assert "Bu sefer biz karar veremedik" in body
    assert f'href="{FEED}"' in body
    assert "<html" in body
    assert "og:url" not in body  # request yokken og:url atlanır


@pytest.mark.django_db
def test_csrf_failure_shows_turkish_page_without_technical_reason():
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        reverse("accounts:login"), {"username": "a@example.com", "password": "x"}
    )
    body = response.content.decode()

    assert response.status_code == 403
    assert "Bu sayfanın süresi dolmuş" in body
    assert f'href="{FEED}"' in body
    assert f'href="{reverse("accounts:login")}"' in body
    for technical in ("CSRF", "Origin", "cookie", "token"):
        assert technical not in body


@pytest.mark.django_db
def test_csrf_failure_page_has_correct_title_and_is_html():
    client = Client(enforce_csrf_checks=True)
    response = client.post(reverse("accounts:register"), {})

    assert response.status_code == 403
    assert "<title>Sayfanın süresi dolmuş — kararsızım</title>" in response.content.decode()


@pytest.mark.django_db
def test_404_shows_the_logged_in_username_in_the_header(client, django_user_model):
    member = django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password="Guclu-Parola-123"
    )
    client.force_login(member)

    body = client.get("/yok-boyle-bir-sayfa/").content.decode()

    assert "@uye" in body
    assert "uye@example.com" not in body
