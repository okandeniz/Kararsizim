"""İstemci IP'sini güvenle okuma ve ham değeri saklamadan özetleme."""

import re

import pytest
from django.test import RequestFactory

from .identity import (
    client_ip,
    ip_subject,
    normalize_email_key,
    normalize_ip,
    subject_hash,
    user_subject,
)

factory = RequestFactory()


def request(**meta):
    return factory.get("/", **meta)


# ---------- normalize_ip ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("203.0.113.9", "203.0.113.9"),
        ("  203.0.113.9  ", "203.0.113.9"),
        ("::ffff:203.0.113.9", "203.0.113.9"),  # IPv4-eşlemeli IPv6 → IPv4
        ("2001:db8:aaaa:bbbb:1:2:3:4", "2001:db8:aaaa:bbbb::"),  # IPv6 → /64 öneki
        ("2001:db8:aaaa:bbbb:ffff:ffff:ffff:ffff", "2001:db8:aaaa:bbbb::"),
    ],
)
def test_normalize_ip(raw, expected):
    assert normalize_ip(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", "bu-bir-ip-degil", "999.1.1.1", "1.2.3", "<script>", "unknown"]
)
def test_normalize_ip_rejects_garbage(raw):
    assert normalize_ip(raw) is None


def test_addresses_in_the_same_ipv6_64_share_a_subject():
    a = request(REMOTE_ADDR="2001:db8:aaaa:bbbb::1")
    b = request(REMOTE_ADDR="2001:db8:aaaa:bbbb:9:9:9:9")
    c = request(REMOTE_ADDR="2001:db8:aaaa:cccc::1")  # başka /64

    assert ip_subject(a) == ip_subject(b)
    assert ip_subject(a) != ip_subject(c)


# ---------- client_ip: güvenilmeyen ortam ----------


def test_without_a_trusted_proxy_forwarding_headers_are_ignored(settings):
    settings.TRUST_PROXY_IP_HEADERS = False
    spoofed = request(REMOTE_ADDR="203.0.113.9", HTTP_X_FORWARDED_FOR="6.6.6.6")

    assert client_ip(spoofed) == "203.0.113.9"  # istemci başlıkla IP değiştiremez


def test_without_a_trusted_proxy_all_proxy_headers_are_ignored(settings):
    settings.TRUST_PROXY_IP_HEADERS = False
    spoofed = request(
        REMOTE_ADDR="203.0.113.9",
        HTTP_X_VERCEL_FORWARDED_FOR="6.6.6.6",
        HTTP_X_REAL_IP="7.7.7.7",
    )

    assert client_ip(spoofed) == "203.0.113.9"


def test_invalid_remote_addr_gives_no_ip(settings):
    settings.TRUST_PROXY_IP_HEADERS = False
    assert client_ip(request(REMOTE_ADDR="")) is None


# ---------- client_ip: Vercel ----------


def test_on_vercel_the_vercel_header_wins(settings):
    settings.TRUST_PROXY_IP_HEADERS = True
    req = request(
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_VERCEL_FORWARDED_FOR="198.51.100.7",
        HTTP_X_FORWARDED_FOR="192.0.2.1",
    )

    assert client_ip(req) == "198.51.100.7"


def test_on_vercel_x_forwarded_for_is_the_fallback(settings):
    settings.TRUST_PROXY_IP_HEADERS = True
    assert (
        client_ip(request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="192.0.2.1")) == "192.0.2.1"
    )


def test_on_vercel_the_first_address_of_a_list_is_the_client(settings):
    settings.TRUST_PROXY_IP_HEADERS = True
    req = request(HTTP_X_FORWARDED_FOR="198.51.100.7, 10.1.1.1, 10.2.2.2")

    assert client_ip(req) == "198.51.100.7"


def test_on_vercel_an_invalid_header_falls_through_to_the_next(settings):
    settings.TRUST_PROXY_IP_HEADERS = True
    req = request(HTTP_X_VERCEL_FORWARDED_FOR="çöp", HTTP_X_FORWARDED_FOR="192.0.2.1")

    assert client_ip(req) == "192.0.2.1"


def test_on_vercel_without_a_header_remote_addr_is_not_used(settings):
    # REMOTE_ADDR orada proxy adresi olabilir: kullanılırsa tüm siteyi tek kova yapar.
    settings.TRUST_PROXY_IP_HEADERS = True

    assert client_ip(request(REMOTE_ADDR="10.0.0.1")) is None
    assert ip_subject(request(REMOTE_ADDR="10.0.0.1")) is None  # IP'ye bağlı sınırlar atlanır


# ---------- Özetleme ----------


def test_subject_hash_is_stable_and_hex():
    assert subject_hash("a", "b") == subject_hash("a", "b")
    assert re.fullmatch(r"[0-9a-f]{32}", subject_hash("a", "b"))


def test_subject_hash_distinguishes_inputs_and_part_boundaries():
    assert subject_hash("a", "b") != subject_hash("a", "c")
    assert subject_hash("ab", "c") != subject_hash("a", "bc")  # ayırıcı sayesinde karışmaz


def test_subject_hash_never_contains_the_raw_value():
    assert "203.0.113.9" not in subject_hash("203.0.113.9")
    assert "ali@example.com" not in subject_hash("login-email", "ali@example.com")


def test_subject_hash_depends_on_the_secret_key(settings):
    settings.SECRET_KEY = "anahtar-bir-" + "x" * 40
    first = subject_hash("203.0.113.9")
    settings.SECRET_KEY = "anahtar-iki-" + "y" * 40

    assert subject_hash("203.0.113.9") != first  # anahtarsız çözülemez, sözlükle denenemez


def test_ip_subject_with_agent_separates_devices_behind_one_ip(settings):
    settings.TRUST_PROXY_IP_HEADERS = False
    iphone = request(REMOTE_ADDR="203.0.113.9", HTTP_USER_AGENT="iPhone")
    android = request(REMOTE_ADDR="203.0.113.9", HTTP_USER_AGENT="Android")

    assert ip_subject(iphone, with_agent=True) != ip_subject(android, with_agent=True)
    assert ip_subject(iphone) == ip_subject(android)  # yalnızca IP ile aynı


def test_long_user_agents_are_truncated_not_rejected(settings):
    settings.TRUST_PROXY_IP_HEADERS = False
    long_agent = request(REMOTE_ADDR="203.0.113.9", HTTP_USER_AGENT="x" * 5000)

    assert re.fullmatch(r"[0-9a-f]{32}", ip_subject(long_agent, with_agent=True))


def test_user_subject_is_per_user():
    class Fake:
        def __init__(self, pk):
            self.pk = pk

    assert user_subject(Fake(1)) == user_subject(Fake(1))
    assert user_subject(Fake(1)) != user_subject(Fake(2))


# ---------- Giriş kilidi anahtarı (incelemeden) ----------

ACCOUNT = "kisi@example.com"


@pytest.mark.parametrize(
    "variant",
    [
        "KISI@Example.COM",  # büyük/küçük harf
        "  kisi@example.com  ",  # boşluk
        "ｋｉｓｉ@ｅｘａｍｐｌｅ.ｃｏｍ",  # tam genişlikli (Django NFKC ile ASCII yapar)
        "\u212aisi@example.com",  # Kelvin işareti (NFKC: K)
        "kısı@example.com",  # noktasız ı (Postgres iexact: UPPER ile aynı hesap)
        "kiſi@example.com",  # uzun s (Postgres iexact: UPPER ile aynı hesap)
    ],
)
def test_email_key_collapses_every_variant_that_reaches_the_same_account(variant):
    assert normalize_email_key(variant) == normalize_email_key(ACCOUNT) == ACCOUNT


def test_email_key_keeps_different_accounts_apart():
    assert normalize_email_key("baska@example.com") != normalize_email_key(ACCOUNT)


def test_email_key_is_bounded_and_survives_garbage():
    assert len(normalize_email_key("x" * 5000)) == 254
    assert normalize_email_key("") == ""
    assert normalize_email_key("a\x00b@example.com")  # NUL çökertmez


def test_on_vercel_all_invalid_headers_give_no_ip(settings):
    settings.TRUST_PROXY_IP_HEADERS = True
    req = request(
        HTTP_X_VERCEL_FORWARDED_FOR="çöp",
        HTTP_X_FORWARDED_FOR="999.1.1.1",
        HTTP_X_REAL_IP="bozuk",
        REMOTE_ADDR="10.0.0.1",
    )

    assert client_ip(req) is None


def test_on_vercel_a_broken_real_ip_header_does_not_hide_a_good_one(settings):
    settings.TRUST_PROXY_IP_HEADERS = True
    req = request(HTTP_X_FORWARDED_FOR="192.0.2.1", HTTP_X_REAL_IP="bozuk")

    assert client_ip(req) == "192.0.2.1"
