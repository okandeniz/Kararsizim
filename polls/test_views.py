import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_feed_returns_200(client):
    response = client.get(reverse("polls:feed"))
    assert response.status_code == 200
    assert "kararsızım" in response.content.decode()


def test_feed_is_at_root(client):
    assert reverse("polls:feed") == "/"


def test_feed_does_not_expose_email(client, django_user_model):
    django_user_model.objects.create_user(
        email="gizli@example.com", username="gizli", password="Guclu-Parola-123"
    )
    client.login(username="gizli@example.com", password="Guclu-Parola-123")
    body = client.get(reverse("polls:feed")).content.decode()
    assert "gizli@example.com" not in body
    assert "@gizli" in body
