"""Oylama yardımcıları: oy sahibi kimliği (üye veya imzalı çerez) ve sonuç hesaplama.

Akış ve detay sayfaları aynı `attach_results` fonksiyonunu kullanır; böylece sayfa başına sorgu
sayısı anket sayısından bağımsız ve sabit kalır.
"""

import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, prefetch_related_objects

from .models import Option, Vote

VOTER_COOKIE = "voter_id"
VOTER_COOKIE_SALT = "kararsizim-voter"
VOTER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 yıl


def read_voter_token(request) -> uuid.UUID | None:
    """İmzalı `voter_id` çerezini okur. Yoksa, bozuksa veya imzası geçersizse None döner."""
    raw = request.get_signed_cookie(
        VOTER_COOKIE, default=None, salt=VOTER_COOKIE_SALT, max_age=VOTER_COOKIE_MAX_AGE
    )
    if raw is None:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def set_voter_cookie(response, token: uuid.UUID) -> None:
    response.set_signed_cookie(
        VOTER_COOKIE,
        str(token),
        salt=VOTER_COOKIE_SALT,
        max_age=VOTER_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )


def voter_filter(request) -> dict | None:
    """Ziyaretçinin oylarını bulmak için `Vote` filtresi. Üye → user, anonim → voter_token.

    Çerezi olmayan anonim ziyaretçinin henüz oyu yoktur; bu durumda None döner.
    """
    if request.user.is_authenticated:
        return {"user": request.user}
    token = read_voter_token(request)
    return {"voter_token": token} if token else None


def attach_results(polls, voter: dict | None) -> list:
    """Anketlere sonuçları ve ziyaretçinin oyunu ekler. Sabit sayıda sorgu çalıştırır.

    Her ankete şunlar eklenir: `results` (seçenek başına sayı, yüzde, lider/seçim işareti),
    `total_votes`, `has_voted`, `chosen_option_id`.
    """
    polls = list(polls)
    if not polls:
        return polls

    prefetch_related_objects(
        polls,
        Prefetch(
            "options",
            queryset=Option.objects.annotate(vote_count=Count("votes")).order_by("position"),
        ),
    )

    chosen = {}
    if voter:
        votes = Vote.objects.filter(poll_id__in=[poll.pk for poll in polls], **voter)
        chosen = dict(votes.values_list("poll_id", "option_id"))

    for poll in polls:
        options = list(poll.options.all())
        total = sum(option.vote_count for option in options)
        top = max((option.vote_count for option in options), default=0)
        chosen_id = chosen.get(poll.pk)

        poll.total_votes = total
        poll.has_voted = chosen_id is not None
        poll.chosen_option_id = chosen_id
        poll.results = [
            {
                "id": option.pk,
                "number": position,  # 1–5: seçenek rengi (--c1…--c5)
                "text": option.text,
                "count": option.vote_count,
                "percent": round_percent(option.vote_count, total),
                "is_leader": top > 0 and option.vote_count == top,
                "is_choice": option.pk == chosen_id,
            }
            for position, option in enumerate(options, start=1)
        ]
    return polls


def round_percent(count: int, total: int) -> int:
    """Yüzdeyi yarım yukarı yuvarlar. Hiç oy yoksa 0 döner (sıfıra bölme yok)."""
    if total == 0:
        return 0
    return int(count * 100 / total + 0.5)


def claim_anonymous_votes(user, token: uuid.UUID | None) -> int:
    """Tarayıcının (imzalı çerez kimliği) anonim oylarını `user` hesabına bağlar.

    İşlenen anonim oy sayısını döner. Kurallar:
    - O ankette hesabın oyu yoksa anonim oy hesaba geçer. Çerez kimliği (`voter_token`) oyda kalır;
      böylece çıkış yapılıp aynı çerezle aynı ankete tekrar anonim oy verilemez.
    - Hesabın o ankette zaten oyu varsa hesabın oyu kalır, anonim kopya silinir ve çerez kimliği
      hesabın oyuna yazılır (aynı nedenle).
    - Başka bir hesaba bağlanmış oylara dokunulmaz.
    Eşzamanlı oy gibi nadir bir çakışmada hiçbir şey değişmez (girişi bozmaz).
    """
    if token is None:
        return 0
    anonymous = list(Vote.objects.filter(voter_token=token, user__isnull=True))
    if not anonymous:
        return 0

    own = dict(
        Vote.objects.filter(
            user=user, poll_id__in=[vote.poll_id for vote in anonymous]
        ).values_list("poll_id", "pk")
    )
    claim_ids = [vote.pk for vote in anonymous if vote.poll_id not in own]
    duplicate_ids = [vote.pk for vote in anonymous if vote.poll_id in own]
    own_ids = [own[vote.poll_id] for vote in anonymous if vote.poll_id in own]

    try:
        with transaction.atomic():
            # Sıra önemli: önce kopyayı sil (çerez kimliği boşalsın), sonra kimliği hesaba yaz.
            Vote.objects.filter(pk__in=duplicate_ids).delete()
            Vote.objects.filter(pk__in=own_ids, voter_token__isnull=True).update(voter_token=token)
            Vote.objects.filter(pk__in=claim_ids).update(user=user)
    except IntegrityError:
        return 0
    return len(anonymous)
