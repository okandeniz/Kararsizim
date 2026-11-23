"""İstemci kimliği: IP'yi güvenle okuma ve ham değeri saklamadan özetleme.

Hız sınırları ham IP, e-posta veya kullanıcı kimliğiyle değil, bunların HMAC özetiyle anahtarlanır.
"""

import ipaddress
import logging
import unicodedata

from django.conf import settings
from django.utils.crypto import salted_hmac

logger = logging.getLogger(__name__)

# Vercel istemci IP'sini bu başlıklara yazar ve dış IP'leri iletmez (sahteciliğe karşı; Vercel
# dokümanı). x-vercel-forwarded-for, önünde başka bir proxy olsa da ezilmez; öncelik onda.
PROXY_IP_HEADERS = ("HTTP_X_VERCEL_FORWARDED_FOR", "HTTP_X_FORWARDED_FOR", "HTTP_X_REAL_IP")

HASH_SALT = "kararsizim.abuse"
HASH_LENGTH = 32  # 128 bit: çakışma için fazlasıyla yeterli, tabloyu küçük tutar


def normalize_ip(raw: str) -> str | None:
    """Geçerli IP'yi normalize eder, değilse None. IPv6 /64 önekine indirilir, IPv4-eşlemeli IPv4'e.

    /64: tek bir ev/hat genellikle /64 alır; önek içinde adres döndürerek sınırı aşmayı zorlaştırır.
    """
    try:
        ip = ipaddress.ip_address(raw.strip())
    except ValueError:
        return None
    if ip.version == 6:
        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False).network_address)
    return str(ip)


def client_ip(request) -> str | None:
    """İstemci IP'si; güvenilir bir kaynak yoksa None (o zaman IP'ye bağlı sınırlar atlanır).

    Vercel'de (`TRUST_PROXY_IP_HEADERS`) yalnızca proxy başlıklarına güvenilir, `REMOTE_ADDR` ise
    kullanılmaz: orada proxy'nin adresi olabilir ve herkes tek kovaya düşer. Başka ortamlarda
    başlıklar istemci tarafından sahtelenebilir, bu yüzden yalnızca `REMOTE_ADDR` okunur.
    """
    if getattr(settings, "TRUST_PROXY_IP_HEADERS", False):
        for header in PROXY_IP_HEADERS:
            value = request.META.get(header, "")
            if value:
                ip = normalize_ip(value.split(",")[0])
                if ip:
                    return ip
        logger.warning("İstemci IP'si okunamadı: proxy başlığı yok. IP'ye bağlı sınırlar atlandı.")
        return None
    return normalize_ip(request.META.get("REMOTE_ADDR", ""))


def subject_hash(*parts: str) -> str:
    """Parçaları (IP, e-posta, kullanıcı kimliği...) saklanabilir bir HMAC özetine çevirir."""
    # algorithm açıkça verilir: Django 6.1'in varsayılanı hâlâ sha1 (2028'de değişecek).
    digest = salted_hmac(HASH_SALT, "\x1f".join(parts), algorithm="sha256")
    return digest.hexdigest()[:HASH_LENGTH]


def ip_subject(request, *, with_agent: bool = False) -> str | None:
    """İstemcinin özeti (IP, istenirse tarayıcı bilgisiyle birlikte). IP okunamazsa None.

    Mobil operatörlerde çok sayıda kullanıcı aynı IP'yi paylaşabilir (CGNAT); tarayıcı bilgisi
    bunları kısmen ayırır (kesin değildir: aynı model telefonların bilgisi benzerdir).
    """
    ip = client_ip(request)
    if ip is None:
        return None
    if with_agent:
        return subject_hash(ip, request.META.get("HTTP_USER_AGENT", "")[:200])
    return subject_hash(ip)


def normalize_email_key(raw: str) -> str:
    """Giriş kilidi için e-posta anahtarı: kimlik doğrulamanın göreceği hesapla aynı olmalı.

    Django'nun kullanıcı adı alanı girdiyi NFKC'ye çevirir ve veritabanı e-postayı büyük/küçük harf
    duyarsız arar (Postgres UPPER ile karşılaştırır: noktasız ı, ſ gibi harfler de aynı hesaba denk
    gelir; tam genişlikli harfler ve Kelvin işareti NFKC ile ASCII'ye iner). Anahtar ham metinden
    üretilseydi bu varyantların her biri ayrı bir kova olur, e-posta başına sınır işlemezdi.
    Çok fazla harfi tek anahtara katmak güvenli yöndedir (kilit biraz daha geniş kapsar).
    """
    text = unicodedata.normalize("NFKC", raw).strip()
    return text.upper().lower()[:254]


def user_subject(user) -> str:
    return subject_hash("user", str(user.pk))
