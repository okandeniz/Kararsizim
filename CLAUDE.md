# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# kararsızım

Kullanıcıların kararsız kaldıkları konularda 2–5 seçenekli anket açıp diğer kullanıcılara danıştığı
bir Django web uygulaması. PROTOTİP aşamasındayız: basit tut, gereksiz soyutlama ve bağımlılık ekleme.

Proje fazlara bölünmüş geliştiriliyor. Tek doğru kaynak: `docs/KARARSIZIM_PLAN.md` (veri modeli
Bölüm 4, URL haritası Bölüm 5, tasarım sistemi Bölüm 6, faz prompt'ları Bölüm 8). Yalnızca
ihtiyaç duyduğun bölümü oku. **Durum:** Faz 0–2 bitti (iskelet, `accounts.User`, tasarım token'ları,
kayıt/giriş/çıkış). Sıradaki: Faz 3 (anket oluşturma). `polls` uygulaması şimdilik yalnızca geçici bir
feed view'ı içeriyor; Poll/Option/Vote modelleri Faz 3'te eklenecek. Header'daki "Anket oluştur" butonu
şimdilik `#`'e bağlı (Faz 3'te `polls:create`).

## Ortam (Windows)
- Sanal ortam `.venv` (Python 3.12). Komutları `.venv\Scripts\python` ile çalıştır
  (bash'te `.venv/Scripts/python`). Sistem Python'u 3.11'dir, KULLANMA. Aşağıda `python` = venv python'u.
- **Port 8000 bu makinede kullanılamıyor** (izin hatası / başka servis). `runserver 8765` gibi başka port kullan.
- Node.js kurulu değil: arayüz kontrolü için Playwright yerine uygulamanın yerleşik tarayıcısını kullan.

## Komutlar
```
python manage.py runserver 8765          # statik dosyalar için .env'de DEBUG=True olmalı
python manage.py makemigrations && python manage.py migrate
python -m pytest                         # tüm testler
python -m pytest accounts/test_models.py::test_str_returns_username_not_email   # tek test
python -m pytest -k "username"           # isimle filtre
python -m ruff check . --fix && python -m ruff format .
python manage.py check                   # bitirmeden önce geçmeli (Stop hook'u da çalıştırır)
python manage.py check --deploy
```
Testler `accounts/test_*.py` ve `polls/test_*.py` içinde (uygulama içi, `tests/` klasörü yok);
pytest ayarı `pyproject.toml`'da. `ruff` `migrations/` ve `docs/` klasörlerini atlar.

## Mimari (birden fazla dosyayı okumadan görünmeyenler)

**Ayarlar (`config/settings.py`)** tamamen ortam değişkenleriyle yönetilir; `.env.example` listeyi tutar.
- `DEBUG` varsayılanı **False**. Yerelde `.env`'de `DEBUG=True` olmadan `runserver` statik dosya sunmaz.
- `SECRET_KEY` yoksa yerel bir geliştirme anahtarına düşer; yalnızca `VERCEL` ortam değişkeni
  tanımlıyken (production) hata verir. Böylece `.env` olmadan da `check`/`pytest` çalışır.
- `DATABASE_URL` boşsa SQLite. Doluysa `conn_max_age=0` + `ssl_require=True`; URL `:6543` (Supabase
  transaction pooler) içeriyorsa `DISABLE_SERVER_SIDE_CURSORS=True` otomatik eklenir. Migration'lar
  production'a **session pooler (5432)** ile yerelden elle uygulanır.
- `DEBUG=False` iken secure cookie ve `SECURE_PROXY_SSL_HEADER` açılır (`SECURE_SSL_REDIRECT` kapalı; Vercel zaten HTTPS).

**Kullanıcı modeli (`accounts`)** — `AUTH_USER_MODEL = "accounts.User"`, ilk migration'dan beri.
- Giriş alanı e-posta (`USERNAME_FIELD="email"`). `UserManager.get_by_natural_key` e-postayı
  `iexact` arar, `save()` e-postayı küçük harfe çevirir; `UniqueConstraint(Lower("email"))` ise `update()` /
  `bulk_create` gibi `save()`'i atlayan yollarda da karışık harfli kopyaları engeller (yoksa giriş
  `MultipleObjectsReturned` ile 500 verirdi).
- `username` büyük/küçük harf duyarsız benzersizdir: alan `unique=True` + `UniqueConstraint(Lower("username"))`.
  Format/yasaklı ad doğrulaması model validator'larında (`username_validators`), form'larda tekrar yazma.
- `User.__str__` kullanıcı adını döndürür. `AbstractBaseUser.__str__` e-posta döndürdüğü için bu
  bilerek ezildi: `{{ user }}` ve `str(user)` e-postayı sızdırmamalı. Admin e-postayı gösterebilir (yalnızca süper kullanıcı).

**Anket akışı (Faz 3–4'te yazılacak, tasarım kararları plan Bölüm 4–5'te)**
- Tek oy kuralı veritabanı kısıtıyla korunur: `Vote` üzerinde `(poll, user)` ve `(poll, voter_token)` için
  koşullu `UniqueConstraint`, ayrıca "user veya voter_token dolu olmalı" `CheckConstraint`.
  View `IntegrityError`'ı yakalar; doğrulama yalnızca view'da bırakılmaz.
- Anonim oy için imzalı `voter_id` çerezi (UUID). Oy URL'si hem normal form (302) hem `fetch`
  (`X-Requested-With: fetch` → `_poll_results.html` parçası) isteğine cevap verir; kart ve sonuç parçaları
  akış ve detay sayfasında ortaktır.
- URL isimleri `polls:feed|detail|vote|create`, `accounts:register|login|logout` (son üçü Faz 2'de hazır).

**Üyelik akışı (`accounts/views.py`, `forms.py`)**
- `next` yönlendirmeleri `safe_next_url()` ile doğrulanır (kayıt ve giriş aynı yardımcıyı kullanır; `LoginView`
  kendi güvenli `next`'ini şablona `next` olarak verir). `/kayit/` ↔ `/giris/` bağlantıları `next`'i taşır.
- Kayıt formu e-posta çakışmasını `iexact` kontrol eder (model `unique` büyük/küçük harfe duyarlı olduğundan
  yoksa 500 verirdi). Giriş formu geçersiz ve pasif hesapta aynı genel mesajı gösterir.
- Çıkış `LogoutView` (yalnızca POST); header'da CSRF'li küçük form olarak durur.
- Form alanları `templates/accounts/_field.html` ile render edilir; ipuçları Django `help_text`'i (Django
  `aria-describedby` ve `aria-invalid`'ı otomatik ekler).

**Ön yüz** — tek `static/css/app.css` (tüm renk/ölçü `:root` token'larından; seçenek renkleri `--c1…--c5`
`Option.position`'a göre) ve tek `static/js/app.js`. Build adımı yok.

## Değişmez kurallar
- E-posta HİÇBİR şablonda, JSON yanıtında veya hata mesajında gösterilmez; kullanıcı her yerde `@kullaniciadi`.
- Tüm doğrulamalar (2–5 seçenek, uzunluklar, tek oy) SUNUCU tarafında yapılır; JS yalnızca deneyim içindir.
  Formlar JS olmadan çalışmalı (progressive enhancement).
- POST formlarında `{% csrf_token %}`, fetch'te `X-CSRFToken`. Şablonlarda `|safe` / `mark_safe` yok.
- `.env` okunmaz/değiştirilmez (izinlerle de engelli); gizli bilgiler yalnızca ortam değişkenlerinden.
- Arayüz metinleri Türkçe; kod, model ve değişken adları İngilizce.
- Yeni pip bağımlılığı eklemeden önce sor.
- Liste sorgularında N+1'den kaçın (`select_related`, `prefetch_related`, `annotate`).

## Çalışma şekli
- Yalnızca istenen fazı uygula, sonraki fazlara geçme. `/faz N` skill'i planı okuyup uygular.
- Hook'lar (`.claude/settings.json`): `.py` düzenlemesinden sonra ruff format/fix çalışır ve kalan lint
  hatası olursa düzeltmeni ister; bitirmeden önce `manage.py check` çalışır, hata varsa bitirtmez.
  Hook'lar `.venv\Scripts\python.exe` ile çalışır, PATH'e güvenmez.
- Bitti saymadan önce `manage.py check` ve `python -m pytest` geçmeli; her yeni view için test yaz.
- Fazın sonunda kısa özet ve kullanıcının elle denemesi gereken adımları yaz; `django-reviewer` alt ajanı
  fazları incelemek için tanımlı.
