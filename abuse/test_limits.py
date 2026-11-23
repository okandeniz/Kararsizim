"""Hız sınırlayıcının mantığı: pencere, kapsam yalıtımı, sızdırmazlık ve hata durumunda davranış."""

from datetime import timedelta

import pytest
from django.db import DatabaseError, InterfaceError
from django.utils import timezone

from .limits import ALLOWED, Limit, attempt, check, purge_old, record
from .models import Hit
from .responses import wait_text

pytestmark = pytest.mark.django_db

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
LIMIT = Limit("test", ((3, MINUTE),))
SUBJECT = "a" * 32


def hit_at(seconds_ago, scope="test", subject=SUBJECT):
    return Hit.objects.create(
        scope=scope, subject=subject, created_at=timezone.now() - timedelta(seconds=seconds_ago)
    )


# ---------- Temel davranış ----------


def test_allows_until_the_limit_then_blocks():
    assert [attempt(LIMIT, SUBJECT).allowed for _ in range(4)] == [True, True, True, False]


def test_blocked_decision_tells_when_to_retry():
    for _ in range(3):
        attempt(LIMIT, SUBJECT)
    decision = attempt(LIMIT, SUBJECT)

    assert not decision.allowed
    assert 1 <= decision.retry_after <= 60


def test_blocked_attempts_are_not_recorded():
    for _ in range(6):
        attempt(LIMIT, SUBJECT)
    assert Hit.objects.count() == 3  # engellenen denemeler engeli uzatmaz


def test_check_never_records():
    for _ in range(5):
        assert check(LIMIT, SUBJECT).allowed
    assert not Hit.objects.exists()


def test_record_adds_exactly_one_row():
    record(LIMIT, SUBJECT)
    assert Hit.objects.get().scope == "test"


# ---------- Pencere ----------


def test_hits_outside_the_window_do_not_count():
    for _ in range(3):
        hit_at(120)  # pencere 60 sn

    assert check(LIMIT, SUBJECT).allowed


def test_retry_after_is_when_the_oldest_hit_leaves_the_window():
    hit_at(50)
    hit_at(30)
    hit_at(10)
    decision = check(LIMIT, SUBJECT)

    assert not decision.allowed
    assert 9 <= decision.retry_after <= 11  # en eski kayıt 10 sn sonra pencereden çıkar


def test_each_window_is_checked_and_the_longest_wait_wins():
    two_windows = Limit("multi", ((2, MINUTE), (3, HOUR)))
    for _ in range(3):
        hit_at(1800, scope="multi")  # 30 dk önce: dakika penceresinde yok, saat penceresinde 3

    decision = check(two_windows, SUBJECT)

    assert not decision.allowed
    assert 1795 <= decision.retry_after <= 1805  # saat penceresi: 3600 - 1800


def test_short_window_can_block_while_long_window_is_fine():
    two_windows = Limit("multi", ((2, MINUTE), (100, HOUR)))
    attempt(two_windows, SUBJECT)
    attempt(two_windows, SUBJECT)

    assert not check(two_windows, SUBJECT).allowed


# ---------- Yalıtım ----------


def test_subjects_are_isolated():
    for _ in range(3):
        attempt(LIMIT, SUBJECT)

    assert not check(LIMIT, SUBJECT).allowed
    assert check(LIMIT, "b" * 32).allowed


def test_scopes_are_isolated():
    other = Limit("other", ((3, MINUTE),))
    for _ in range(3):
        attempt(LIMIT, SUBJECT)

    assert check(other, SUBJECT).allowed


def test_suffix_scopes_a_limit_per_object():
    for _ in range(3):
        attempt(LIMIT, SUBJECT, suffix="1")

    assert not check(LIMIT, SUBJECT, suffix="1").allowed
    assert check(LIMIT, SUBJECT, suffix="2").allowed
    assert check(LIMIT, SUBJECT).allowed  # soneksiz kapsam ayrıdır


# ---------- Özne yok / kapalı ----------


def test_missing_subject_is_allowed_and_not_recorded():
    # IP okunamadıysa (ör. proxy başlığı yok) IP'ye bağlı sınır atlanır; herkes tek kovaya düşmez.
    assert [attempt(LIMIT, None).allowed for _ in range(10)] == [True] * 10
    assert not Hit.objects.exists()


def test_emergency_switch_turns_every_limit_off(settings):
    settings.RATE_LIMITS_ENABLED = False

    assert [attempt(LIMIT, SUBJECT).allowed for _ in range(10)] == [True] * 10
    assert not Hit.objects.exists()


# ---------- Temizlik ----------


def test_purge_old_removes_only_expired_rows():
    hit_at(2 * 24 * 3600)  # 2 gün önce
    recent = hit_at(3600)  # 1 saat önce

    assert purge_old() == 1
    assert list(Hit.objects.all()) == [recent]


def test_record_sometimes_purges_old_rows(monkeypatch):
    hit_at(3 * 24 * 3600)
    monkeypatch.setattr("abuse.limits.random.random", lambda: 0.0)  # temizlik tetiklensin

    record(LIMIT, SUBJECT)

    assert Hit.objects.count() == 1  # eski silindi, yeni kaldı


def test_record_does_not_purge_when_the_dice_say_no(monkeypatch):
    hit_at(3 * 24 * 3600)
    monkeypatch.setattr("abuse.limits.random.random", lambda: 0.99)

    record(LIMIT, SUBJECT)

    assert Hit.objects.count() == 2


# ---------- Hata durumunda siteyi çökertmez ----------


def boom(*args, **kwargs):
    raise DatabaseError("tablo yok")


def test_check_fails_open_when_the_database_errors(monkeypatch):
    monkeypatch.setattr(Hit.objects, "filter", boom)
    assert check(LIMIT, SUBJECT) is ALLOWED


def test_record_swallows_database_errors(monkeypatch):
    monkeypatch.setattr(Hit.objects, "create", boom)
    assert record(LIMIT, SUBJECT) is None


def test_attempt_fails_open_when_the_table_is_missing(monkeypatch):
    # Migration henüz uygulanmamışsa oy/giriş/kayıt 500 vermemeli.
    monkeypatch.setattr(Hit.objects, "filter", boom)
    monkeypatch.setattr(Hit.objects, "create", boom)

    assert attempt(LIMIT, SUBJECT).allowed


# ---------- Bekleme metni ----------


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (1, "birkaç saniye"),
        (59, "birkaç saniye"),
        (60, "1 dakika"),
        (61, "2 dakika"),
        (300, "5 dakika"),
        (3600, "60 dakika"),
        (7200, "yaklaşık 2 saat"),
        (86400, "yaklaşık 24 saat"),
    ],
)
def test_wait_text(seconds, expected):
    assert wait_text(seconds) == expected


# ---------- Bağlantı hataları (incelemeden) ----------


def drop_connection(*args, **kwargs):
    # Kopan pooler bağlantısı InterfaceError verir; bu DatabaseError'ın alt sınıfı DEĞİLDİR.
    raise InterfaceError("connection already closed")


def test_check_fails_open_on_interface_errors(monkeypatch):
    monkeypatch.setattr(Hit.objects, "filter", drop_connection)
    assert check(LIMIT, SUBJECT) is ALLOWED


def test_record_swallows_interface_errors(monkeypatch):
    monkeypatch.setattr(Hit.objects, "create", drop_connection)
    assert record(LIMIT, SUBJECT) is None


def test_purge_errors_never_break_a_request(monkeypatch):
    monkeypatch.setattr("abuse.limits.random.random", lambda: 0.0)  # temizlik tetiklensin
    monkeypatch.setattr("abuse.limits.purge_old", drop_connection)

    record(LIMIT, SUBJECT)  # istisna fırlatmaz

    assert Hit.objects.count() == 1  # kayıt yazıldı


def test_login_ip_limit_also_has_an_hourly_window():
    from . import rules

    assert any(window == HOUR for _, window in rules.LOGIN_IP.windows)  # parola püskürtmeye karşı


def test_admin_changelist_works_without_a_scope_filter(client, django_user_model):
    django_user_model.objects.create_superuser(
        email="patron@example.com", username="patron", password="Guclu-Parola-123"
    )
    client.login(username="patron@example.com", password="Guclu-Parola-123")
    for poll_id in range(30):
        Hit.objects.create(scope=f"guest_vote_poll:{poll_id}", subject="a" * 32)

    changelist = client.get("/admin/abuse/hit/")
    search = client.get("/admin/abuse/hit/?q=guest_vote_poll:7")

    assert changelist.status_code == 200
    assert "aaaaaaaa" in changelist.content.decode()  # yalnızca özetin ilk 8 karakteri
    assert "a" * 32 not in changelist.content.decode()
    assert search.status_code == 200
    assert client.get("/admin/abuse/hit/add/").status_code == 403  # kayıtlar elle eklenmez
