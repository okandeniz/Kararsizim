---
name: ui-kontrol
description: Çalışan uygulamayı tarayıcıda açıp arayüzü tasarım sistemine göre kontrol eder. Arayüz değişikliklerinden sonra kullan.
argument-hint: "[sayfa-yolu, ör. / veya /anket/yeni/]"
---

1. Sunucu çalışmıyorsa `python manage.py runserver` ile arka planda başlat.
2. Uygulamanın yerleşik tarayıcısıyla (`mcp__Claude_Browser__*` araçları) http://127.0.0.1:8000$ARGUMENTS
   sayfasını aç. Sayfa yolu verilmediyse /, /anket/yeni/, /kayit/ ve bir anket detayını gez.
   (Playwright MCP bu projede kurulu değil; Node.js yok.)
3. Her sayfayı 390px (mobil) ve 1280px (masaüstü) genişlikte kontrol et
   (`resize_window` ile). Bitince pencereyi `desktop` ön ayarına döndür.
4. docs/KARARSIZIM_PLAN.md "6. Tasarım sistemi" bölümüne göre değerlendir:
   renkler, boşluklar, köşe yuvarlaklığı, okunabilirlik, odak (focus) stilleri, taşmalar.
5. Konsolda JS hatası var mı bak (`read_console_messages`).
6. Sorunları listele ve düzelt. Ardından tekrar kontrol et.
