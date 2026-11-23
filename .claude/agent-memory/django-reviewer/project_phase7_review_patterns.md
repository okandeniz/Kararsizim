---
name: phase7-review-patterns
description: Kararsizim Faz 7 (abuse/ hiz siniri, kayit honeypot, giris kilidi) incelemesi: bulunan kaliplar ve dogrulanan iyi uygulamalar
metadata:
  type: project
---

Faz 7 incelemesinde (2026-11) kritik bulgu yok. Tekrar kontrol edilecek maddeler:
- protect_login (abuse/decorators.py) e-posta kilit anahtarini ham `strip().lower()` ile uretir; Django AuthenticationForm ise NFKC normalize eder ve DB `iexact` (Postgres UPPER) kullanir -> fullwidth/Kelvin/dotless-i (ı, ſ) varyantlariyla e-posta basina kilit atlatilir. Oneri: `unicodedata.normalize("NFKC", v).strip().upper().lower()`.
- RegisterForm.__init__ gecersiz form_ts'i TAZE belirteçle degistiriyor, clean() sonra o taze belirteci dogruluyor: yalnizca REGISTER_MIN_FILL_SECONDS>0 oldugu icin reddediliyor (yavas DB ile clean_email >2 sn surerse gecer). Oneri: gecerliligi degistirmeden ONCE bir bayrakta sakla.
- limits.py yalnizca DatabaseError yakaliyor; django.db.InterfaceError (kopan pooler baglantisi) 500 verir. Oneri: `except django.db.Error`.
- LOGIN_IP yalnizca 20/dk penceresi var (saatlik/gunluk yok); parola puskurtme icin gevsek.
- Hit.scope anket basina sonekli (guest_vote_poll:<pk>) -> admin list_filter her anket icin ayri deger.

Dogrulanan iyi uygulamalar: pencere matematigi (n>=max iken en eski kayit cikinca bir azalir, reddedilen sayilmaz), purge RETENTION(25sa) > en uzun pencere (24sa), HMAC salted_hmac sha256 + ham IP/e-posta DB/log/429'da yok, 429 sayfasinda kullanici girdisi yok (sabit mesaj), kilit mesaji hesap varligini sizdirmiyor, X-Forwarded-For yalnizca VERCEL'de, IPv6 scope-id/ipv4-mapped 500 vermiyor, JS 429'u text/plain hata olarak gosteriyor, honeypot inert+aria-hidden+tabindex=-1, protect_login 200=basarisiz varsayimi Django LoginView/admin login icin dogru (302 basari).

**Why:** Sonraki incelemede ayni maddeleri bastan arama, once giderilip giderilmedigine bak.
**How to apply:** abuse/ veya giris/kayit akisina dokunan degisikliklerde bu listeyi kontrol et.
