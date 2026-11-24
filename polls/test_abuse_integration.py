"""Oy ve anket oluşturma için hız sınırları (view düzeyi)."""

import re
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse

from abuse.limits import Limit
from abuse.models import Hit
from abuse.rules import GUEST_VOTE_PER_POLL

from .conftest import PASSWORD
from .models import Poll, Vote

pytestmark = pytest.mark.django_db

FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}
MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def vote_url(poll):
    return reverse("polls:vote", kwargs={"pk": poll.pk})


def detail_url(poll):
    return reverse("polls:detail", kwargs={"pk": poll.pk})


def option_id(poll, position=0):
    return poll.options.all()[position].pk


def vote_as(client, poll, **extra):
    return client.post(vote_url(poll), {"option": option_id(poll)}, **FETCH, **extra)


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password=PASSWORD
    )


def limit_votes(monkeypatch, maximum):
    monkeypatch.setattr("polls.views.VOTE", Limit("vote", ((maximum, MINUTE),)))


def limit_guest_votes(monkeypatch, maximum):
    monkeypatch.setattr(
        "polls.views.GUEST_VOTE_PER_POLL", Limit("guest_vote_poll", ((maximum, DAY),))
    )


# ---------- Oy: genel hız sınırı ----------


def test_voting_too_fast_returns_429_for_fetch(client, poll, monkeypatch):
    limit_votes(monkeypatch, 3)

    # 1. oy kaydedilir (200), 2-3. "zaten oy verdin" (409) ama DENEME sayılır, 4-5. engellenir.
    codes = [vote_as(client, poll).status_code for _ in range(5)]

    assert codes == [200, 409, 409, 429, 429]
    assert Vote.objects.count() == 1


def test_fetch_429_is_plain_text_with_retry_after(client, poll, monkeypatch):
    limit_votes(monkeypatch, 1)
    vote_as(client, poll)

    response = vote_as(client, poll)

    assert response.status_code == 429
    assert response["Content-Type"].startswith("text/plain")
    assert response.content.decode() == "Çok hızlı gidiyorsun, biraz bekleyip tekrar dene."
    assert 1 <= int(response["Retry-After"]) <= 60


def test_form_post_is_redirected_back_with_a_message(client, poll, monkeypatch):
    limit_votes(monkeypatch, 1)
    client.post(vote_url(poll), {"option": option_id(poll)})  # 1. deneme

    response = client.post(vote_url(poll), {"option": option_id(poll)}, follow=True)

    assert response.redirect_chain[-1][0] == detail_url(poll)
    assert "Çok hızlı gidiyorsun" in response.content.decode()
    assert Vote.objects.count() == 1


def test_the_limit_applies_to_members_too(client, poll, member, monkeypatch):
    limit_votes(monkeypatch, 2)
    client.force_login(member)

    codes = [vote_as(client, poll).status_code for _ in range(3)]

    assert codes == [200, 409, 429]


def test_throttled_request_is_rejected_before_touching_the_poll(client, monkeypatch):
    limit_votes(monkeypatch, 1)
    client.post(reverse("polls:vote", kwargs={"pk": 999999}), {"option": 1}, **FETCH)

    # Var olmayan ankete gelen sel de sınırlanır (404'ten önce).
    response = client.post(reverse("polls:vote", kwargs={"pk": 999999}), {"option": 1}, **FETCH)

    assert response.status_code == 429


def test_different_user_agents_have_separate_counters(poll, monkeypatch):
    limit_votes(monkeypatch, 1)

    assert vote_as(Client(), poll, HTTP_USER_AGENT="iPhone").status_code == 200
    assert (
        vote_as(Client(), poll, HTTP_USER_AGENT="Android").status_code == 200
    )  # aynı IP, başka cihaz


# ---------- Misafir oyu: anket başına üst sınır ----------


def test_guest_vote_cap_per_poll(poll, make_poll, monkeypatch):
    limit_guest_votes(monkeypatch, 2)

    # Her Client ayrı çerez (çerezi silen biri gibi) ama aynı IP + tarayıcı.
    codes = [vote_as(Client(), poll).status_code for _ in range(3)]

    assert codes == [200, 200, 429]
    assert Vote.objects.filter(poll=poll).count() == 2

    other = make_poll(question="Başka anket")
    assert vote_as(Client(), other).status_code == 200  # üst sınır ankete özeldir


def test_guest_cap_message_points_to_logging_in(poll, monkeypatch):
    limit_guest_votes(monkeypatch, 1)
    vote_as(Client(), poll)

    response = vote_as(Client(), poll)

    assert response.status_code == 429
    assert "Giriş yaparak oy verebilirsin" in response.content.decode()


def test_members_are_not_subject_to_the_guest_cap(poll, member, monkeypatch):
    limit_guest_votes(monkeypatch, 1)
    vote_as(Client(), poll)  # üst sınır doldu
    assert vote_as(Client(), poll).status_code == 429

    logged_in = Client()
    logged_in.force_login(member)

    assert vote_as(logged_in, poll).status_code == 200  # üye oyu hesaba bağlı, çerezle aşılamaz


def test_rejected_duplicate_votes_do_not_use_up_the_guest_cap(poll, monkeypatch):
    limit_guest_votes(monkeypatch, 2)
    first = Client()
    assert vote_as(first, poll).status_code == 200
    for _ in range(3):
        assert vote_as(first, poll).status_code == 409  # yinelenen oy sayılmaz

    assert vote_as(Client(), poll).status_code == 200  # 2. başarılı misafir oyu
    assert vote_as(Client(), poll).status_code == 429


def test_guest_cap_counts_only_successful_votes(poll, monkeypatch):
    limit_guest_votes(monkeypatch, 1)
    bad = Client().post(vote_url(poll), {"option": "999999"}, **FETCH)  # geçersiz seçenek

    assert bad.status_code == 400
    assert vote_as(Client(), poll).status_code == 200  # 400 sınırdan yemedi


def test_changing_user_agent_does_not_reset_the_guest_cap(poll, monkeypatch):
    # User-Agent'ı istemci belirler: sınır yalnızca IP'ye bağlıdır, yoksa her istekte başlığı
    # değiştiren bir betik sınırsız misafir oyu verirdi.
    limit_guest_votes(monkeypatch, 1)
    vote_as(Client(), poll, HTTP_USER_AGENT="bot-1")

    assert vote_as(Client(), poll, HTTP_USER_AGENT="bot-2").status_code == 429


def test_guest_cap_is_separate_per_ip(poll, monkeypatch):
    limit_guest_votes(monkeypatch, 1)
    vote_as(Client(), poll, REMOTE_ADDR="203.0.113.1")

    assert vote_as(Client(), poll, REMOTE_ADDR="203.0.113.1").status_code == 429
    assert vote_as(Client(), poll, REMOTE_ADDR="203.0.113.2").status_code == 200


def test_rotating_user_agents_cannot_exceed_the_default_guest_cap(poll):
    cap = GUEST_VOTE_PER_POLL.windows[0][0]

    codes = [
        vote_as(Client(), poll, HTTP_USER_AGENT=f"bot-{i}").status_code for i in range(cap + 5)
    ]

    assert codes.count(200) == cap
    assert Vote.objects.filter(poll=poll).count() == cap


def test_rotating_user_agents_do_not_bypass_the_ip_ceiling(poll, monkeypatch):
    monkeypatch.setattr("polls.views.VOTE_IP", Limit("vote_ip", ((2, MINUTE),)))

    codes = [vote_as(Client(), poll, HTTP_USER_AGENT=f"bot-{i}").status_code for i in range(4)]

    assert codes == [200, 200, 429, 429]


def test_ip_ceiling_applies_to_members_too(poll, member, monkeypatch):
    monkeypatch.setattr("polls.views.VOTE_IP", Limit("vote_ip", ((1, MINUTE),)))
    client = Client()
    client.force_login(member)
    vote_as(client, poll, HTTP_USER_AGENT="a")

    assert vote_as(client, poll, HTTP_USER_AGENT="b").status_code == 429


# ---------- IP kaynağı ----------


def test_on_vercel_clients_are_told_apart_by_the_forwarded_ip(poll, settings, monkeypatch):
    settings.TRUST_PROXY_IP_HEADERS = True
    limit_votes(monkeypatch, 1)

    first = vote_as(Client(), poll, HTTP_X_VERCEL_FORWARDED_FOR="198.51.100.1")
    again = vote_as(Client(), poll, HTTP_X_VERCEL_FORWARDED_FOR="198.51.100.1")
    other = vote_as(Client(), poll, HTTP_X_VERCEL_FORWARDED_FOR="198.51.100.2")

    assert [first.status_code, again.status_code] == [200, 429]
    assert other.status_code in (200, 409)  # başka IP'nin sayacı ayrı (429 değil)


def test_off_vercel_spoofed_forwarding_headers_do_not_bypass_the_limit(poll, settings, monkeypatch):
    settings.TRUST_PROXY_IP_HEADERS = False
    limit_votes(monkeypatch, 1)

    vote_as(Client(), poll, HTTP_X_FORWARDED_FOR="198.51.100.1")
    spoofed = vote_as(Client(), poll, HTTP_X_FORWARDED_FOR="198.51.100.2")

    assert spoofed.status_code == 429  # aynı REMOTE_ADDR: başlık uydurmak kaçış sağlamaz


def test_on_vercel_without_a_forwarded_ip_the_ip_limits_are_skipped(poll, settings, monkeypatch):
    settings.TRUST_PROXY_IP_HEADERS = True
    limit_votes(monkeypatch, 1)

    codes = [vote_as(Client(), poll).status_code for _ in range(3)]

    assert 429 not in codes  # IP bilinmiyorsa herkesi tek kovaya doldurmayız
    assert not Hit.objects.exists()


# ---------- Gizlilik ve anahtar ----------


def test_hits_never_store_the_raw_ip(client, poll):
    vote_as(client, poll, REMOTE_ADDR="203.0.113.77")

    hits = list(Hit.objects.all())

    assert hits
    for hit in hits:
        assert "203.0.113.77" not in hit.scope + hit.subject
        assert re.fullmatch(r"[0-9a-f]{32}", hit.subject)


def test_emergency_switch_disables_the_vote_limit(client, poll, settings, monkeypatch):
    settings.RATE_LIMITS_ENABLED = False
    limit_votes(monkeypatch, 1)

    codes = [vote_as(client, poll).status_code for _ in range(4)]

    assert 429 not in codes
    assert not Hit.objects.exists()


def test_vote_still_works_if_the_abuse_table_is_unavailable(client, poll, monkeypatch):
    from django.db import DatabaseError

    def boom(*args, **kwargs):
        raise DatabaseError("tablo yok")

    monkeypatch.setattr(Hit.objects, "filter", boom)
    monkeypatch.setattr(Hit.objects, "create", boom)

    assert vote_as(client, poll).status_code == 200  # koruma devre dışı kalır, site çökmez


# ---------- Anket oluşturma ----------


def post_poll(client, question="Soru", options=("A", "B")):
    return client.post(reverse("polls:create"), {"question": question, "option": list(options)})


def test_poll_creation_is_limited_per_user(client, member, monkeypatch):
    monkeypatch.setattr("polls.views.POLL_CREATE", Limit("poll_create", ((2, HOUR),)))
    client.force_login(member)

    codes = [post_poll(client, question=f"Soru {i}").status_code for i in range(3)]

    assert codes == [302, 302, 429]
    assert Poll.objects.count() == 2


def test_poll_limit_page_is_branded_and_has_retry_after(client, member, monkeypatch):
    monkeypatch.setattr("polls.views.POLL_CREATE", Limit("poll_create", ((1, HOUR),)))
    client.force_login(member)
    post_poll(client)

    response = post_poll(client)
    body = response.content.decode()

    assert response.status_code == 429
    assert "Biraz yavaşla" in body
    assert "Kısa sürede çok fazla anket oluşturdun." in body
    assert 1 <= int(response["Retry-After"]) <= 3600


def test_invalid_poll_submissions_do_not_count(client, member, monkeypatch):
    monkeypatch.setattr("polls.views.POLL_CREATE", Limit("poll_create", ((2, HOUR),)))
    client.force_login(member)

    for _ in range(5):
        assert post_poll(client, options=("Tek",)).status_code == 200  # doğrulama hatası

    assert [post_poll(client, question=f"Soru {i}").status_code for i in range(2)] == [302, 302]


def test_poll_limit_is_per_user_not_global(client, member, django_user_model, monkeypatch):
    monkeypatch.setattr("polls.views.POLL_CREATE", Limit("poll_create", ((1, HOUR),)))
    other = django_user_model.objects.create_user(
        email="baska@example.com", username="baska", password=PASSWORD
    )
    client.force_login(member)
    assert post_poll(client).status_code == 302
    assert post_poll(client).status_code == 429

    other_client = Client()
    other_client.force_login(other)

    assert post_poll(other_client).status_code == 302


def test_viewing_the_create_form_is_not_limited(client, member, monkeypatch):
    monkeypatch.setattr("polls.views.POLL_CREATE", Limit("poll_create", ((1, HOUR),)))
    client.force_login(member)

    assert [client.get(reverse("polls:create")).status_code for _ in range(5)] == [200] * 5
