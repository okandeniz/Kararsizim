# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# kararsızım

Kullanıcıların kararsız kaldıkları konularda 2–5 seçenekli anket açıp diğer kullanıcılara danıştığı
bir Django web uygulaması. PROTOTİP aşamasındayız: basit tut, gereksiz soyutlama ve bağımlılık ekleme.

Proje fazlara bölünmüş geliştiriliyor. Tek doğru kaynak: `docs/KARARSIZIM_PLAN.md` (veri modeli
Bölüm 4, URL haritası Bölüm 5, tasarım sistemi Bölüm 6, faz prompt'ları Bölüm 8). Yalnızca
ihtiyaç duyduğun bölümü oku. **Durum:** Faz 0–4 bitti (iskelet, `accounts.User`, tasarım token'ları,
kayıt/giriş/çıkış, anket oluşturma, akış ve oylama): yerelde çalışan prototip hazır. Sıradaki: Faz 5
(Supabase + Vercel). Faz 2–4 `django-reviewer` ile incelendi. Plan Faz 8'deki "oy birleştirme" öne
çekilip yapıldı (aşağıda); plan dosyasındaki "bilinen sınırlama" notu artık eski.

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
Testler `accounts/`, `polls/` ve `config/` içinde `test_*.py` olarak durur (uygulama içi, `tests/` klasörü yok);
pytest ayarı `pyproject.toml`'da. `ruff` `migrations/` ve `docs/` klasörlerini atlar.

## Mimari (birden fazla dosyayı okumadan görünmeyenler)

**Ayarlar (`config/settings.py`)** tamamen ortam değişkenleriyle yönetilir; `.env.example` listeyi tutar.
- `DEBUG` varsayılanı **False**. Yerelde `.env`'de `DEBUG=True` olmadan `runserver` statik dosya sunmaz.
- `SECRET_KEY` yoksa yerel bir geliştirme anahtarına düşer; yalnızca `VERCEL` ortam değişkeni
  tanımlıyken (production) hata verir. Böylece `.env` olmadan da `check`/`pytest` çalışır.
- `DATABASE_URL` boşsa SQLite. Doluysa `conn_max_age=0` + `ssl_require=True`; URL `:6543` (Supabase
  transaction pooler) içeriyorsa `DISABLE_SERVER_SIDE_CURSORS=True` ve `OPTIONS["prepare_threshold"]=None` otomatik eklenir
  (Supabase transaction modu hazırlanmış ifadeleri desteklemez; psycopg3 5. sorguda otomatik hazırlardı).
  Port `dj_database_url`'den tamsayı gelir, `DISABLE_SERVER_SIDE_CURSORS` anahtarı her zaman vardır (`False`). Migration'lar
  production'a **session pooler (5432)** ile yerelden elle uygulanır.
- `DEBUG=False` iken secure cookie ve `SECURE_PROXY_SSL_HEADER` açılır (`SECURE_SSL_REDIRECT` kapalı; Vercel zaten HTTPS).
- `MAILERS` (konsol backend) yalnızca `DEBUG=True` iken tanımlıdır: Django 6.1 `check --deploy` konsol backend'ini
  hata sayar (`mail.E001`). `check --deploy`'da yalnızca `W004` (HSTS) ve `W008` (SSL redirect) uyarıları beklenir.
- Ortam değişkeni davranışı `config/test_settings_env.py` ile test edilir (modülü reload eder; `.env` etkisiz).

**Kullanıcı modeli (`accounts`)** — `AUTH_USER_MODEL = "accounts.User"`, ilk migration'dan beri.
- Giriş alanı e-posta (`USERNAME_FIELD="email"`). `UserManager.get_by_natural_key` e-postayı
  `iexact` arar, `save()` e-postayı küçük harfe çevirir; `UniqueConstraint(Lower("email"))` ise `update()` /
  `bulk_create` gibi `save()`'i atlayan yollarda da karışık harfli kopyaları engeller (yoksa giriş
  `MultipleObjectsReturned` ile 500 verirdi).
- `username` büyük/küçük harf duyarsız benzersizdir: alan `unique=True` + `UniqueConstraint(Lower("username"))`.
  Format/yasaklı ad doğrulaması model validator'larında (`username_validators`), form'larda tekrar yazma.
- `User.__str__` kullanıcı adını döndürür. `AbstractBaseUser.__str__` e-posta döndürdüğü için bu
  bilerek ezildi: `{{ user }}` ve `str(user)` e-postayı sızdırmamalı. Admin e-postayı gösterebilir (yalnızca süper kullanıcı).

**Anket oluşturma (`polls/forms.py`, `views.py`)**
- `PollForm` normal bir `forms.Form`: soru + aynı adlı 5 `option` input'u (`request.POST.getlist`). Tüm kurallar
  (boşları at, 2–5 adet, 80 karakter, büyük/küçük harf duyarsız tekrar, boşluk normalizasyonu) `clean()`'de;
  `save(author)` Poll + Option'ları tek `transaction.atomic` içinde yazar (position 0..n-1). Seçenek hataları
  non-field error olarak seçenek grubunun altında gösterilir; girilen değerler `option_slots` ile korunur.
  `normalize_text` NFC'ye çevirir ve NUL/kontrol ile görünmez/yön değiştiren karakterleri siler (Postgres NUL'u
  reddeder, SQLite etmez: yerelde görünmeyen 500!). Kullanıcı metni kaydeden yeni alanlar da bundan geçmeli.
  Admin'de `OptionInlineFormSet` aynı 2–5 kuralını uygular (`min_num`/`max_num` tek başına doğrulamaz).
- `create` view'ı `login_required_with_message` ile korunur (misafiri `?next=` ile girişe atar ve giriş
  sayfasında mesaj gösterir). Sınırlar `polls/models.py` sabitlerinde (`MAX_OPTIONS` vb.), form ve admin
  aynı sabitleri kullanır.
- `create.html`'de 5 kutu da HTML'de bulunur; "+ Seçenek ekle" ve × butonları `hidden` gelir, yalnızca JS
  (`initPollForm`) açar. Seçenek rengi kutunun `data-position` (1–5) değerinden gelir (CSS'te `--opt`).
  JS × ile silince alttaki değerleri yukarı kaydırır, böylece renk sırası bozulmaz.

**Akış ve oylama (`polls/voting.py`, `views.py`, `_poll_*.html`)**
- Tek oy kuralı veritabanı kısıtıyla korunur: `Vote` üzerinde `(poll, user)` ve `(poll, voter_token)` için
  koşullu `UniqueConstraint`, ayrıca "user veya voter_token dolu olmalı" `CheckConstraint`. `vote` view'ı
  `IntegrityError`'ı yakalar (fetch → 409, form → mesaj + yönlendirme). `Option.position < 5` de DB
  `CheckConstraint`'iyle korunur. DB, seçeneğin ankete ait olmasını zorlamaz; `vote` view'ı bunu
  `Option.objects.filter(pk=…, poll=poll)` ile doğrular (değilse 400).
- Oy sahibi: üye → `user`; anonim → imzalı `voter_id` çerezi (UUID, `salt="kararsizim-voter"`, 1 yıl,
  httponly, Lax, `secure=not DEBUG`). Bozuk/sahte çerez yok sayılır ve yenisi üretilir. `voter_filter(request)`
  `Vote` filtresini verir (çerezsiz anonim için `None`).
- **Oy birleştirme (`claim_anonymous_votes`, `polls/signals.py`):** `user_logged_in` sinyali (kayıt, giriş ve
  admin girişi) ile tarayıcının anonim oyları hesaba bağlanır; `vote` view'ı da üyeler için aynısını oy
  vermeden önce çağırır (sinyali kaçıran eski oturumlar için). Bağlanan oyda `voter_token` SİLİNMEZ: böylece
  çıkış yapıp aynı çerezle aynı ankete anonim oy verilemez. Hesabın o ankette zaten oyu varsa hesabın oyu
  kalır, anonim kopya silinir ve çerez kimliği hesabın oyuna yazılır. Başka hesaba bağlı oylara dokunulmaz.
  **Açık kalan:** üye oy verip çıkış yaparsa anonim tekrar oy verebilir (üye oyunda çerez kimliği yok);
  çerez silme/başka tarayıcı/gizli pencere de engellenemez (Faz 7: oran sınırı ve bot koruması).
- **Sorgu sayısı sabit olmalı:** akış ve detay `attach_results(polls, voter)` kullanır (seçenekler `Prefetch` +
  `annotate(Count("votes"))`, ziyaretçinin oyları tek sorgu). Toplam/yüzde/lider/seçim Python'da hesaplanır
  (`poll.results`, `poll.total_votes`, `poll.has_voted`); şablonda sorgu yapma. `test_feed.py` bunu doğrular.
- `_poll_card.html` hem akışta hem detayda ortak; oy durumuna göre `_poll_vote_form.html` veya
  `_poll_results.html` gösterir. Oy URL'si normal form (302) ve `fetch` (`X-Requested-With: fetch` →
  `_poll_results.html` parçası, hata → kısa `text/plain` + 400/409) isteğine cevap verir; JS
  (`initVoting`) parçayı kartın içine koyar ve çubukları 0'dan doldurur. Form `next` alanı sayfa +
  `#poll-<id>` taşır.
- URL isimleri `polls:feed|detail|vote|create`, `accounts:register|login|logout`.

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
- Yeni pip bağımlılığı eklemeden önce sor. Üretim bağımlılıkları hem `requirements.txt` hem `pyproject.toml`
  `dependencies` içinde tutulur (Vercel ikisinden birini kullanabilir); `config/test_dependencies.py` eşitliği
  doğrular, ikisine birden ekle. Dev araçları (pytest, ruff) yalnızca `requirements-dev.txt`'tedir.
- Liste sorgularında N+1'den kaçın (`select_related`, `prefetch_related`, `annotate`).

## Çalışma şekli
- Yalnızca istenen fazı uygula, sonraki fazlara geçme. `/faz N` skill'i planı okuyup uygular.
- Hook'lar (`.claude/settings.json`): `.py` düzenlemesinden sonra ruff format/fix çalışır ve kalan lint
  hatası olursa düzeltmeni ister; bitirmeden önce `manage.py check` çalışır, hata varsa bitirtmez.
  Hook'lar `.venv\Scripts\python.exe` ile çalışır, PATH'e güvenmez. Türkçe Windows'un varsayılan kodlaması
  cp1254'tür: hook'larda stdin/alt süreç çıktısı/stderr açıkça UTF-8 işlenir (yeni hook yazarsan
  `subprocess.run(..., encoding="utf-8", errors="replace")` kullan; aksi halde Türkçe çıktıda çöker).
- `manage.py check` (Stop hook'u dahil) kullanıcının `.env`'indeki hatalı `DATABASE_URL` yüzünden
  `ImproperlyConfigured` ile düşerse `.env`'i OKUMA/değiştirme: kullanıcıdan satırı düzeltmesini ya da boşaltmasını
  iste. Kendi doğrulamalarını `DATABASE_URL= python manage.py check` / `DATABASE_URL= python -m pytest` ile çalıştır
  (`python-dotenv` tanımlı değişkeni ezmez; boş değer SQLite demektir).
- Bitti saymadan önce `manage.py check` ve `python -m pytest` geçmeli; her yeni view için test yaz.
- Fazın sonunda kısa özet ve kullanıcının elle denemesi gereken adımları yaz; `django-reviewer` alt ajanı
  fazları incelemek için tanımlı.
