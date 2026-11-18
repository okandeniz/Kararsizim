---
name: poll-vote-review-patterns
description: Kararsizim Faz 3-4 (anket/oylama) incelemesinde bulunan kalıplar ve doğrulanan iyi uygulamalar
metadata:
  type: project
---

Prod DB Supabase Postgres (DATABASE_URL), testler SQLite. SQLite'ta görünmeyen Postgres farklarını ara (ör. NUL karakteri `\x00` ValueError -> 500).

Faz 3-4'te bulunan tekrar eden/önemli sorunlar:
- PollForm seçenek metninde NUL/zero-width/kontrol karakteri filtrelenmiyor (question CharField ProhibitNullCharacters alır, options almaz).
- IntegrityError yakalama vote view'ında tek `except` ile hem "zaten oy verdi" hem FK ihlalini 409 yapıyor.
- Admin OptionInline min_num/max_num yalnızca UI; validate_min/validate_max verilmedi, sunucu kuralıyla tam uyumlu değil. Inline'dan seçenek silmek oyları CASCADE siler.
- Fetch 409'da JS sonuçları göstermiyor (hata + form kalıyor).

Doğrulanan iyi uygulamalar: vote view csrf'siz değil, option poll=poll filtresiyle doğrulanıyor, int() + OverflowError yakalanıyor, imzalı çerez salt+max_age+default=None, attach_results sabit sorgu (prefetch+Count tek join), DB unique constraint'leri (user/token partial), safe_next_url fragment/page ile uyumlu, innerHTML yalnızca kendi şablon fragment'i, e-posta sızıntısı yok.

**How to apply:** Sonraki fazlarda yeni form/model girdilerinde NUL ve görünmez karakter, admin inline doğrulamasını ve Postgres'e özgü davranışı kontrol et.
