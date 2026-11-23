from functools import wraps

from .identity import ip_subject, normalize_email_key, subject_hash
from .limits import attempt, check, record
from .responses import rate_limited_page
from .rules import LOGIN_FAILURE_EMAIL, LOGIN_IP


def protect_login(view):
    """Giriş görünümünü (site girişi ve /admin/ girişi) kaba kuvvet denemesine karşı korur.

    - IP başına dakikada en fazla 20 POST.
    - E-posta başına 15 dakikada en fazla 10 BAŞARISIZ giriş. Sınır dolunca doğru parola bile
      denenmez (yoksa saldırgan sınırın ardından denemeye devam eder). Mesaj, e-posta kayıtlı olsun
      olmasın aynıdır: hesap varlığı sızmaz.
    - Başarısız giriş, formun hatayla yeniden çizilmesi (HTTP 200) olarak anlaşılır; başarı 302'dir.

    Not: bir saldırgan bilinen bir e-posta için 10 başarısız deneme yaparak o hesabı 15 dakika
    kilitleyebilir. Kaba kuvvet korumasının bilinen bedeli; kilit süresi kısa tutuldu.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)

        email = normalize_email_key(request.POST.get("username") or "")
        email_subject = subject_hash("login-email", email) if email else None

        decision = check(LOGIN_FAILURE_EMAIL, email_subject)
        if not decision.allowed:
            return rate_limited_page(
                request, decision, "Çok fazla başarısız giriş denemesi yapıldı."
            )
        decision = attempt(LOGIN_IP, ip_subject(request))
        if not decision.allowed:
            return rate_limited_page(
                request, decision, "Bu ağdan çok fazla giriş denemesi yapıldı."
            )

        response = view(request, *args, **kwargs)
        if response.status_code == 200:
            record(LOGIN_FAILURE_EMAIL, email_subject)
        return response

    return wrapper
