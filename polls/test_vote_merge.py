"""Oy birleştirme: giriş/kayıt sırasında tarayıcının anonim oyları hesaba bağlanır."""

import time

import pytest
from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.test import Client
from django.urls import reverse

from accounts.forms import make_form_token

from .conftest import PASSWORD
from .models import Vote
from .voting import claim_anonymous_votes

pytestmark = pytest.mark.django_db

LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
REGISTER_URL = reverse("accounts:register")
FEED_URL = reverse("polls:feed")
FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


def vote_url(poll):
    return reverse("polls:vote", kwargs={"pk": poll.pk})


def option_id(poll, position=0):
    return poll.options.all()[position].pk


def log_in(client, email="uye@example.com"):
    response = client.post(LOGIN_URL, {"username": email, "password": PASSWORD})
    assert response.status_code == 302


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password=PASSWORD
    )


@pytest.fixture
def other_member(django_user_model):
    return django_user_model.objects.create_user(
        email="baska@example.com", username="baska", password=PASSWORD
    )


# ---------- Giriş sırasında bağlama ----------


def test_anonymous_vote_is_attributed_to_account_on_login(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    anonymous = Vote.objects.get()

    log_in(client)

    vote = Vote.objects.get()
    assert vote.pk == anonymous.pk
    assert vote.user == member
    assert vote.option_id == option_id(poll, 0)
    assert vote.voter_token == anonymous.voter_token  # çerez kimliği oyda kalır


def test_after_login_poll_shows_results_with_own_choice(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll, 1)})
    log_in(client)

    body = client.get(FEED_URL).content.decode()

    assert "data-results" in body
    assert "data-vote-form" not in body
    assert body.count("result--chosen") == 1


def test_voting_again_after_login_is_rejected(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    log_in(client)

    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, **FETCH)

    assert response.status_code == 409
    assert Vote.objects.count() == 1
    assert Vote.objects.get().option_id == option_id(poll, 0)


def test_all_polls_voted_anonymously_are_claimed(client, make_poll, member):
    polls = [make_poll(question=f"Soru {i}") for i in range(3)]
    for poll in polls:
        client.post(vote_url(poll), {"option": option_id(poll)})

    log_in(client)

    assert Vote.objects.count() == 3
    assert set(Vote.objects.values_list("user", flat=True)) == {member.pk}


def test_register_claims_anonymous_votes(client, poll, django_user_model):
    client.post(vote_url(poll), {"option": option_id(poll)})

    client.post(
        REGISTER_URL,
        {
            "username": "yeni",
            "email": "yeni@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "hp_alan": "",
            "form_ts": make_form_token(time.time() - 10),
        },
    )

    vote = Vote.objects.get()
    assert vote.user == django_user_model.objects.get(username="yeni")


def test_login_without_cookie_leaves_other_browsers_votes_alone(client, poll, member):
    Client().post(vote_url(poll), {"option": option_id(poll)})  # başka tarayıcı

    log_in(client)  # bu tarayıcıda çerez yok

    assert Vote.objects.get().user is None


def test_only_this_browsers_votes_are_claimed(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    Client().post(vote_url(poll), {"option": option_id(poll, 1)})  # başka tarayıcı

    log_in(client)

    assert Vote.objects.count() == 2
    assert Vote.objects.filter(user=member).count() == 1
    assert Vote.objects.filter(user__isnull=True).count() == 1


# ---------- Hesabın zaten oyu varsa ----------


def test_account_vote_wins_over_anonymous_duplicate(client, poll, member):
    other_browser = Client()
    other_browser.force_login(member)
    other_browser.post(vote_url(poll), {"option": option_id(poll, 1)})  # hesabın oyu
    client.post(vote_url(poll), {"option": option_id(poll, 0)})  # bu tarayıcıdan anonim
    token = Vote.objects.get(user__isnull=True).voter_token

    log_in(client)

    vote = Vote.objects.get()
    assert vote.user == member
    assert vote.option_id == option_id(poll, 1)  # hesabın oyu kaldı
    assert vote.voter_token == token  # çerez kimliği hesabın oyuna yazıldı


def test_logout_then_anonymous_vote_is_blocked_after_duplicate_merge(client, poll, member):
    other_browser = Client()
    other_browser.force_login(member)
    other_browser.post(vote_url(poll), {"option": option_id(poll, 1)})
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    log_in(client)
    client.post(LOGOUT_URL)

    response = client.post(vote_url(poll), {"option": option_id(poll, 2)}, **FETCH)

    assert response.status_code == 409
    assert Vote.objects.count() == 1


# ---------- Çıkış sonrası ve başka hesaplar ----------


def test_logout_then_anonymous_vote_with_same_cookie_is_blocked(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    log_in(client)
    client.post(LOGOUT_URL)

    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, **FETCH)

    assert response.status_code == 409
    assert Vote.objects.count() == 1


def test_after_logout_feed_still_shows_the_browsers_vote(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    log_in(client)
    client.post(LOGOUT_URL)

    body = client.get(FEED_URL).content.decode()

    assert "data-results" in body
    assert "result--chosen" in body


def test_claimed_votes_are_not_taken_by_another_account(client, poll, member, other_member):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    log_in(client)
    client.post(LOGOUT_URL)

    log_in(client, "baska@example.com")  # aynı tarayıcıda başka hesap

    assert Vote.objects.get().user == member
    # Diğer hesap kendi oyunu verebilir (paylaşılan bilgisayar engellenmez).
    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, **FETCH)
    assert response.status_code == 200
    assert Vote.objects.filter(user=other_member).count() == 1
    assert Vote.objects.count() == 2


# ---------- Oy anında bağlama (giriş sinyalinin kaçırdığı durum) ----------


def test_vote_view_claims_leftover_anonymous_vote_of_logged_in_user(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    client.force_login(member)  # sahte istek: çerez yok, giriş sinyali bağlama yapmaz
    assert Vote.objects.get().user is None

    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, **FETCH)

    assert response.status_code == 409
    vote = Vote.objects.get()
    assert vote.user == member
    assert vote.option_id == option_id(poll, 0)


# ---------- Fonksiyon davranışı ----------


def test_claim_without_token_does_nothing(poll, member):
    assert claim_anonymous_votes(member, None) == 0


def test_claim_is_idempotent(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll)})
    token = Vote.objects.get().voter_token

    assert claim_anonymous_votes(member, token) == 1
    assert claim_anonymous_votes(member, token) == 0
    assert Vote.objects.get().user == member


def test_claim_conflict_does_not_break_login(client, poll, member, monkeypatch):
    client.post(vote_url(poll), {"option": option_id(poll)})

    def boom(self, **kwargs):
        raise IntegrityError("eşzamanlı çakışma")

    monkeypatch.setattr(QuerySet, "update", boom)
    response = client.post(LOGIN_URL, {"username": "uye@example.com", "password": PASSWORD})

    assert response.status_code == 302
    assert "_auth_user_id" in client.session
    assert Vote.objects.get().user is None  # hiçbir şey değişmedi


def test_login_form_errors_do_not_claim_votes(client, poll, member):
    client.post(vote_url(poll), {"option": option_id(poll)})

    client.post(LOGIN_URL, {"username": "uye@example.com", "password": "yanlis-parola"})

    assert Vote.objects.get().user is None
