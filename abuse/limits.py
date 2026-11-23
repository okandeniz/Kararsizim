"""Veritabanı tabanlı hız sınırlayıcı.

Vercel serverless olduğu için bellek içi sayaç istekler arasında paylaşılmaz; sayaçlar `Hit`
tablosundadır. Her denetim tek bir toplama sorgusudur (tüm pencereler birlikte), kayıt tek ekleme.

Sınırlayıcı İSTEĞİ DÜŞÜRMEZ: veritabanı hatasında loglar ve izin verir (kötüye kullanım koruması
siteyi çökertmemeli). Denetle-sonra-kaydet arasında eşzamanlı isteklerle küçük bir aşım olabilir;
bu bir ödünleşimdir, sınır sıkı bir kota değil kaba bir koruma sayılır.
"""

import logging
import math
import random
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import Error, transaction
from django.db.models import Count, Min, Q
from django.utils import timezone

from .models import Hit

logger = logging.getLogger(__name__)

RETENTION = timedelta(days=1, hours=1)  # en uzun pencere (24 saat) + pay
PURGE_PROBABILITY = 0.02  # eski kayıtlar isteklerin ~%2'sinde temizlenir (zamanlanmış iş yok)


@dataclass(frozen=True)
class Limit:
    """Bir kapsam için bir ya da birkaç pencere: (en fazla, süre) çiftleri."""

    scope: str
    windows: tuple[tuple[int, timedelta], ...]


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0  # saniye: engel ne zaman kalkar (izin verildiyse 0)


ALLOWED = Decision(True)


def enabled() -> bool:
    """Acil durum anahtarı: RATE_LIMITS_ENABLED=False ise sınırlar uygulanmaz."""
    return getattr(settings, "RATE_LIMITS_ENABLED", True)


def scope_name(limit: Limit, suffix: str = "") -> str:
    return f"{limit.scope}:{suffix}" if suffix else limit.scope


def check(limit: Limit, subject: str | None, suffix: str = "") -> Decision:
    """Sınırı aşıp aşmadığına bakar; KAYDETMEZ. Özne yoksa (ör. IP okunamadı) izin verir."""
    if not enabled() or not subject:
        return ALLOWED

    now = timezone.now()
    aggregates = {}
    for index, (_, window) in enumerate(limit.windows):
        in_window = Q(created_at__gt=now - window)
        aggregates[f"n{index}"] = Count("id", filter=in_window)
        aggregates[f"oldest{index}"] = Min("created_at", filter=in_window)
    longest = max(window for _, window in limit.windows)

    try:
        with transaction.atomic():
            row = Hit.objects.filter(
                scope=scope_name(limit, suffix), subject=subject, created_at__gt=now - longest
            ).aggregate(**aggregates)
    except Error:
        logger.exception("Hız sınırı sorgusu başarısız; istek sınırsız geçirildi")
        return ALLOWED

    retry_after = 0
    for index, (maximum, window) in enumerate(limit.windows):
        if row[f"n{index}"] >= maximum:
            # En eski kayıt pencereden çıkınca bu pencerenin sayısı bir azalır.
            wait = math.ceil((row[f"oldest{index}"] + window - now).total_seconds())
            retry_after = max(retry_after, wait, 1)

    if retry_after:
        logger.warning(
            "Hız sınırı aşıldı: kapsam=%s, bekleme=%ss", scope_name(limit, suffix), retry_after
        )
        return Decision(False, retry_after)
    return ALLOWED


def record(limit: Limit, subject: str | None, suffix: str = "") -> None:
    """Bir isteği sayaca ekler. Özne yoksa ya da sınırlar kapalıysa bir şey yapmaz."""
    if not enabled() or not subject:
        return
    try:
        with transaction.atomic():
            Hit.objects.create(scope=scope_name(limit, suffix), subject=subject)
    except Error:
        logger.exception("Hız sınırı kaydı yazılamadı")
        return
    if random.random() < PURGE_PROBABILITY:
        try:
            purge_old()
        except Error:
            logger.exception("Eski hız sınırı kayıtları temizlenemedi")


def attempt(limit: Limit, subject: str | None, suffix: str = "") -> Decision:
    """Denemeyi sayar ve sınır aşılıyorsa reddeder.

    Reddedilen deneme sayılmaz: pencere kendiliğinden kayar, engellenen istemci engelini uzatmaz.
    """
    decision = check(limit, subject, suffix)
    if decision.allowed:
        record(limit, subject, suffix)
    return decision


def purge_old(now=None) -> int:
    """RETENTION'dan eski kayıtları siler; silinen sayıyı döndürür."""
    cutoff = (now or timezone.now()) - RETENTION
    deleted, _ = Hit.objects.filter(created_at__lt=cutoff).delete()
    return deleted
