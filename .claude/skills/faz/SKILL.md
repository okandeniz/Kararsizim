---
name: faz
description: docs/KARARSIZIM_PLAN.md içindeki belirtilen fazı uygular
argument-hint: "[faz-numarası]"
disable-model-invocation: true
---

docs/KARARSIZIM_PLAN.md dosyasında "Faz $0" başlıklı bölümü oku. Bölümdeki
"Claude için prompt" metnini görev olarak al ve kabul kriterlerine uy.

1. Önce kısa bir uygulama planı çıkar ve bana göster.
2. Onaylarsam uygula. Yalnızca bu fazın kapsamındaki işleri yap.
3. `python manage.py check` ve `python -m pytest` çalıştır, hataları düzelt.
4. Bitince: yapılanların özeti, kabul kriterleri kontrol listesi (✅/❌) ve
   benim elle denemem gereken adımlar.
