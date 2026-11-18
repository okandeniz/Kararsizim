# kararsızım

Kullanıcıların kararsız kaldıkları konularda 2–5 seçenekli anket açıp diğer
kullanıcılara danıştığı bir web uygulaması. Şu an PROTOTİP aşamasındayız:
basit tut, gereksiz soyutlama ve bağımlılık ekleme.

Ayrıntılı plan, veri modeli ve tasarım sistemi: docs/KARARSIZIM_PLAN.md
(yalnızca ihtiyaç olduğunda ilgili bölümü oku).

## Teknoloji yığını
- Python 3.12, Django 6.1, Django şablonları
- Frontend: sade HTML + CSS + vanilla JS (framework YOK, npm/build adımı YOK)
- Veritabanı: yerelde SQLite, production'da Supabase Postgres (DATABASE_URL ile)
- Deploy: Vercel (Django zero-config)
- Test: pytest + pytest-django. Kalite: ruff

## Ortam (Windows)
- Sanal ortam: `.venv`. Komutları `.venv\Scripts\python` ile çalıştır
  (bash'te `.venv/Scripts/python`). Sistem Python'u 3.11'dir, KULLANMA.
- Aşağıdaki komutlardaki `python`, venv'in python'udur.

## Komutlar
- Sunucu: `python manage.py runserver` → http://127.0.0.1:8000
- Migration: `python manage.py makemigrations && python manage.py migrate`
- Test: `python -m pytest`
- Lint/format: `python -m ruff check . --fix && python -m ruff format .`
- Sistem kontrolü: `python manage.py check`
- Deploy kontrolü: `python manage.py check --deploy`

## Mimari
- `config/`: settings, urls, wsgi/asgi
- `accounts/`: özel User modeli (e-posta ile giriş, benzersiz kullanıcı adı), kayıt/giriş/çıkış
- `polls/`: Poll, Option, Vote modelleri; akış, detay, oluşturma ve oylama view'ları
- `templates/`: base.html + uygulama klasörleri. Tekrarlanan parçalar `_partial.html` olarak adlandırılır
- `static/css/app.css`: tüm stiller, CSS değişkenleriyle (tasarım token'ları)
- `static/js/app.js`: tüm etkileşimler (fetch ile oy verme, seçenek ekle/çıkar)

## Değişmez kurallar
- AUTH_USER_MODEL = "accounts.User". Kullanıcı modeline bu kural dışında dokunma.
- E-posta adresi HİÇBİR şablonda, JSON yanıtında veya hata mesajında gösterilmez.
  Kullanıcıyı her yerde `@kullaniciadi` olarak göster.
- Tüm doğrulamalar (2–5 seçenek, uzunluklar, tek oy) SUNUCU tarafında yapılır.
  JS doğrulaması yalnızca kullanıcı deneyimi içindir.
- Formlar JS olmadan da çalışmalı. JS bunları geliştirir (progressive enhancement).
- Tüm POST formlarında `{% csrf_token %}` olmalı. fetch isteklerinde X-CSRFToken header'ı gönder.
- Şablonlarda `|safe` ve `mark_safe` kullanma.
- Gizli bilgiler yalnızca ortam değişkenlerinden okunur (`.env` yerelde). `.env` dosyasını okuma, değiştirme.
- Arayüz metinleri Türkçe; kod, model ve değişken adları İngilizce.
- Yeni bir pip bağımlılığı eklemeden önce sor.
- Listelerde N+1 sorgusundan kaçın: `select_related`, `prefetch_related`, `annotate`.

## Çalışma şekli
- Yalnızca istenen fazı uygula, sonraki fazlara geçme.
- Bir işi bitti saymadan önce: `python manage.py check` ve `python -m pytest` geçmeli.
- Her yeni view için en az bir test yaz.
- Faz sonunda değişikliklerin kısa özetini ve kullanıcının elle denemesi gereken adımları yaz.
- Arayüz kontrolü için uygulamanın yerleşik tarayıcısını kullan (Playwright/Node kurulu değil).
