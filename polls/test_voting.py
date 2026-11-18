import uuid

import pytest
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from .conftest import PASSWORD
from .models import Vote
from .voting import VOTER_COOKIE, attach_results, round_percent

pytestmark = pytest.mark.django_db

FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


def vote_url(poll):
    return reverse("polls:vote", kwargs={"pk": poll.pk})


def detail_url(poll):
    return reverse("polls:detail", kwargs={"pk": poll.pk})


def option_id(poll, position=0):
    return poll.options.all()[position].pk


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password=PASSWORD
    )


# ---------- Anonim oy ----------


def test_anonymous_vote_is_saved_with_signed_cookie(client, poll):
    response = client.post(vote_url(poll), {"option": option_id(poll)})

    vote = Vote.objects.get()
    assert response.status_code == 302
    assert vote.user is None
    assert vote.voter_token is not None
    assert vote.option_id == option_id(poll)

    cookie = response.cookies[VOTER_COOKIE]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    assert cookie["max-age"] == 60 * 60 * 24 * 365
    assert cookie["secure"]  # testlerde DEBUG=False
    # İmzalı çerez: "<uuid>:<zaman>:<imza>". Düz UUID değil.
    assert cookie.value.startswith(str(vote.voter_token) + ":")
    assert cookie.value.count(":") == 2


def test_cookie_is_not_secure_in_debug(client, poll, settings):
    settings.DEBUG = True
    response = client.post(vote_url(poll), {"option": option_id(poll)})
    assert not response.cookies[VOTER_COOKIE]["secure"]


def test_second_vote_with_same_cookie_is_rejected(client, poll):
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, follow=True)

    assert Vote.objects.count() == 1
    assert Vote.objects.get().option_id == option_id(poll, 0)
    assert "Bu ankete zaten oy verdin." in response.content.decode()


def test_second_vote_does_not_set_new_cookie(client, poll):
    client.post(vote_url(poll), {"option": option_id(poll)})
    response = client.post(vote_url(poll), {"option": option_id(poll, 1)})
    assert VOTER_COOKIE not in response.cookies


def test_same_cookie_can_vote_on_different_polls(client, make_poll):
    first, second = make_poll(question="Bir"), make_poll(question="İki")
    client.post(vote_url(first), {"option": option_id(first)})
    client.post(vote_url(second), {"option": option_id(second)})

    assert Vote.objects.count() == 2
    assert Vote.objects.values("voter_token").distinct().count() == 1


def test_different_browsers_can_each_vote_once(poll):
    for _ in range(3):
        Client().post(vote_url(poll), {"option": option_id(poll)})
    assert Vote.objects.count() == 3


def test_tampered_cookie_is_ignored_and_replaced(client, poll):
    client.cookies[VOTER_COOKIE] = "sahte-uuid:abc:imza"
    response = client.post(vote_url(poll), {"option": option_id(poll)})

    assert Vote.objects.count() == 1
    assert VOTER_COOKIE in response.cookies
    assert response.cookies[VOTER_COOKIE].value != "sahte-uuid:abc:imza"


def test_unsigned_plain_uuid_cookie_is_not_trusted(client, poll):
    forged = uuid.uuid4()
    client.cookies[VOTER_COOKIE] = str(forged)
    client.post(vote_url(poll), {"option": option_id(poll)})

    assert Vote.objects.get().voter_token != forged


def test_anonymous_voter_who_logs_in_can_vote_again_known_limitation(client, poll, member):
    # Bilinen prototip sınırlaması (plan Bölüm 4): Faz 8'de çözülecek.
    client.post(vote_url(poll), {"option": option_id(poll)})
    client.force_login(member)
    client.post(vote_url(poll), {"option": option_id(poll)})

    assert Vote.objects.count() == 2


# ---------- Üye oyu ----------


def test_member_vote_is_saved_with_user_and_no_cookie(client, poll, member):
    client.force_login(member)
    response = client.post(vote_url(poll), {"option": option_id(poll)})

    vote = Vote.objects.get()
    assert vote.user == member
    assert vote.voter_token is None
    assert VOTER_COOKIE not in response.cookies


def test_member_cannot_vote_twice(client, poll, member):
    client.force_login(member)
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, follow=True)

    assert Vote.objects.count() == 1
    assert "Bu ankete zaten oy verdin." in response.content.decode()


def test_member_may_vote_on_own_poll(client, make_poll, member):
    own = make_poll(poll_author=member)
    client.force_login(member)
    client.post(vote_url(own), {"option": option_id(own)})
    assert Vote.objects.get().user == member


# ---------- Geçersiz istekler ----------


def test_option_from_another_poll_returns_400(client, make_poll):
    first, second = make_poll(question="Bir"), make_poll(question="İki")
    response = client.post(vote_url(first), {"option": option_id(second)})

    assert response.status_code == 400
    assert not Vote.objects.exists()


@pytest.mark.parametrize("value", ["", "abc", "0", "-1", "999999", str(10**30), "1.5"])
def test_invalid_option_values_return_400(client, poll, value):
    response = client.post(vote_url(poll), {"option": value})

    assert response.status_code == 400
    assert not Vote.objects.exists()


def test_missing_option_returns_400(client, poll):
    assert client.post(vote_url(poll), {}).status_code == 400


def test_vote_on_unknown_poll_returns_404(client):
    assert client.post(reverse("polls:vote", kwargs={"pk": 9999}), {"option": 1}).status_code == 404


def test_get_is_not_allowed(client, poll):
    response = client.get(vote_url(poll))
    assert response.status_code == 405


def test_vote_requires_csrf_token(poll):
    csrf_client = Client(enforce_csrf_checks=True)
    response = csrf_client.post(vote_url(poll), {"option": option_id(poll)})

    assert response.status_code == 403
    assert not Vote.objects.exists()


# ---------- Yönlendirme (JS'siz form) ----------


def test_redirects_to_detail_by_default(client, poll):
    response = client.post(vote_url(poll), {"option": option_id(poll)})
    assert response.url == detail_url(poll)


def test_redirects_to_safe_next(client, poll):
    response = client.post(vote_url(poll), {"option": option_id(poll), "next": "/?page=2#poll-5"})
    assert response.url == "/?page=2#poll-5"


@pytest.mark.parametrize(
    "unsafe", ["https://evil.example/", "//evil.example/", "javascript:alert(1)"]
)
def test_unsafe_next_is_ignored(client, poll, unsafe):
    response = client.post(vote_url(poll), {"option": option_id(poll), "next": unsafe})
    assert response.url == detail_url(poll)


def test_success_message_is_shown_after_redirect(client, poll):
    response = client.post(vote_url(poll), {"option": option_id(poll)}, follow=True)
    assert "Oyun kaydedildi" in response.content.decode()


# ---------- fetch isteği ----------


def test_fetch_vote_returns_results_fragment(client, poll):
    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, **FETCH)
    body = response.content.decode()

    assert response.status_code == 200
    assert "<html" not in body
    assert 'data-results data-total="1"' in body
    assert "%100 · 1 oy" in body
    assert "%0 · 0 oy" in body
    assert body.count("result__check") == 1  # yalnızca seçilen seçenekte ✓
    assert VOTER_COOKIE in response.cookies


def test_fetch_vote_marks_choice_and_leader(client, poll):
    other_votes = [Client(), Client()]
    for other in other_votes:
        other.post(vote_url(poll), {"option": option_id(poll, 0)})
    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, **FETCH)
    body = response.content.decode()

    assert "%67 · 2 oy" in body
    assert "%33 · 1 oy" in body
    assert "result--leader" in body
    assert "result--chosen" in body


def test_fetch_invalid_option_returns_400_plain_text(client, poll):
    response = client.post(vote_url(poll), {"option": "999999"}, **FETCH)

    assert response.status_code == 400
    assert response["Content-Type"].startswith("text/plain")
    assert response.content.decode() == "Geçersiz seçenek."


def test_fetch_duplicate_vote_returns_409_plain_text(client, poll):
    client.post(vote_url(poll), {"option": option_id(poll)}, **FETCH)
    response = client.post(vote_url(poll), {"option": option_id(poll, 1)}, **FETCH)

    assert response.status_code == 409
    assert response["Content-Type"].startswith("text/plain")
    assert response.content.decode() == "Bu ankete zaten oy verdin."
    assert Vote.objects.count() == 1


def test_fetch_member_vote_shows_own_choice(client, poll, member):
    client.force_login(member)
    body = client.post(vote_url(poll), {"option": option_id(poll, 2)}, **FETCH).content.decode()
    assert body.count("result__check") == 1
    assert "Senin seçimin" in body


# ---------- Sonuç hesaplama ----------


@pytest.mark.parametrize(
    ("count", "total", "expected"),
    [(0, 0, 0), (0, 5, 0), (1, 3, 33), (2, 3, 67), (1, 2, 50), (5, 5, 100), (1, 8, 13)],
)
def test_round_percent(count, total, expected):
    assert round_percent(count, total) == expected


def test_results_with_no_votes_do_not_divide_by_zero(poll):
    (poll,) = attach_results([poll], voter=None)

    assert poll.total_votes == 0
    assert not poll.has_voted
    assert [result["percent"] for result in poll.results] == [0, 0, 0]
    assert not any(result["is_leader"] for result in poll.results)


def test_tied_leaders_are_both_marked(client, poll):
    for position in (0, 1):
        Client().post(vote_url(poll), {"option": option_id(poll, position)})
    (poll,) = attach_results([poll], voter=None)

    assert [result["is_leader"] for result in poll.results] == [True, True, False]


def test_results_keep_option_order_and_color_numbers(poll):
    (poll,) = attach_results([poll], voter=None)

    assert [result["text"] for result in poll.results] == ["Kırmızı", "Mavi", "Yeşil"]
    assert [result["number"] for result in poll.results] == [1, 2, 3]


# ---------- Detay sayfası ----------


def test_detail_shows_vote_form_before_voting(client, poll):
    body = client.get(detail_url(poll)).content.decode()

    assert "data-vote-form" in body
    assert "csrfmiddlewaretoken" in body
    assert body.count('name="option"') == 3
    assert "data-results" not in body
    assert f'action="{vote_url(poll)}"' in body


def test_detail_shows_results_after_voting(client, poll):
    client.post(vote_url(poll), {"option": option_id(poll, 1)})
    body = client.get(detail_url(poll)).content.decode()

    assert "data-results" in body
    assert "data-vote-form" not in body
    assert "%100 · 1 oy" in body
    assert "1 oy" in body


def test_detail_results_persist_for_member_across_sessions(client, poll, member):
    client.force_login(member)
    client.post(vote_url(poll), {"option": option_id(poll, 0)})

    fresh = Client()
    fresh.force_login(member)
    assert "data-results" in fresh.get(detail_url(poll)).content.decode()


def test_detail_other_voter_still_sees_form(client, poll):
    Client().post(vote_url(poll), {"option": option_id(poll)})
    assert "data-vote-form" in client.get(detail_url(poll)).content.decode()


# ---------- IntegrityError ayrımı (incelemeden) ----------


def test_non_unique_integrity_error_is_not_reported_as_already_voted(client, poll, monkeypatch):
    # Anket/seçenek eşzamanlı silinirse FK ihlali olur; bu "zaten oy verdin" değildir.
    def boom(*args, **kwargs):
        raise IntegrityError("foreign key violation")

    monkeypatch.setattr(Vote.objects, "create", boom)
    response = client.post(vote_url(poll), {"option": option_id(poll)}, **FETCH)

    assert response.status_code == 400
    assert response.content.decode() == "Geçersiz seçenek."
    assert not Vote.objects.exists()


def test_results_fragment_is_focusable_for_screen_readers(client, poll):
    body = client.post(vote_url(poll), {"option": option_id(poll)}, **FETCH).content.decode()
    assert 'tabindex="-1"' in body
