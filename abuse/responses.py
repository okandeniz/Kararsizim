"""Hız sınırı aşılınca verilen yanıtlar (429)."""

import math

from django.http import HttpResponse
from django.shortcuts import render

from .limits import Decision

DEFAULT_MESSAGE = "Çok fazla deneme yaptın."


def wait_text(seconds: int) -> str:
    """Bekleme süresini insan diline çevirir: 'birkaç saniye', '5 dakika', 'yaklaşık 2 saat'."""
    if seconds < 60:
        return "birkaç saniye"
    minutes = math.ceil(seconds / 60)
    if minutes < 90:
        return f"{minutes} dakika"
    return f"yaklaşık {math.ceil(minutes / 60)} saat"


def rate_limited_page(request, decision: Decision, message: str = DEFAULT_MESSAGE):
    """Marka diliyle 429 sayfası (giriş, kayıt, anket oluşturma gibi form sayfaları için)."""
    response = render(
        request,
        "429.html",
        {"message": message, "wait": wait_text(decision.retry_after)},
        status=429,
    )
    response["Retry-After"] = str(decision.retry_after)
    return response


def rate_limited_text(decision: Decision, message: str) -> HttpResponse:
    """fetch isteği için kısa düz metin (oy kartı bunu kartın içinde gösterir)."""
    response = HttpResponse(message, status=429, content_type="text/plain; charset=utf-8")
    response["Retry-After"] = str(decision.retry_after)
    return response
