---
name: phase6-review-patterns
description: Kararsizim Faz 6 (tasarim/OG/hata sayfalari/a11y) tum-kod incelemesi: kalan dusuk bulgular ve dogrulanan iyi uygulamalar
metadata:
  type: project
---

Faz 6 sonu incelemesinde (2026-11) kritik/orta bulgu yok; kalanlar dusuk:
- PollForm.question uzunlugu CharField.max_length ile normalize_text'ten ONCE kontrol ediliyor; NFC bazi karakterlerde (U+0344, U+1D15E) uzatir -> Postgres'te 200'u asabilir (500). Secenekler normalize sonrasi kontrol ediliyor, soru degil.
- username regex hala `^...$` (accounts/models.py): `\Z` onerisi Faz 2'den beri duruyor (formlar strip ettigi icin pratikte dusuk).
- og:url `request.build_absolute_uri` sorgu dizesini icerir (kanonik degil); og_title/og_description detay disinda sayfa basligiyla senkron degil.
- Toast mesajlari 5 sn'de siliniyor (info seviyesi hata mesajlari dahil); her kartta ayni adli "Paylas" linki; .input:focus outline:none (yalnizca 1px border).
- HSTS ayari yok (SECURE_HSTS_SECONDS); SECRET_KEY yedegi VERCEL disinda DEBUG=False'ta da bilinen anahtara duser.
- vote-option--pop sinifi hata sonrasi kalir (animasyon tekrar etmez).

Dogrulanan iyi uygulamalar: 500/403_csrf sablonlari request/user/messages/csrf olmadan guvenli (base.html `{% if request %}`, `user` tanimsiz -> misafir menusu), reason gosterilmiyor; OG/meta ozniteliklerinde autoescape (testli); e-posta yalnizca admin/form alaninda; JS innerHTML yalnizca sunucu parcasi; token'lar test ediliyor (renk yasagi + WCAG).

**Why:** Sonraki incelemede ayni maddeleri tekrar arastirma, once bunlarin giderilip giderilmedigine bak.
**How to apply:** Faz 7 (oran siniri) ve sonrasinda yeni sablon/ayar degisikliklerinde bu listeyi kontrol et.
