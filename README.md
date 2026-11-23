# kararsızım

Kararsız kaldığın konuda 2–5 seçenekli anket açıp diğer kullanıcılara danıştığın bir web uygulaması.
Şu an prototip aşamasında. Ayrıntılı plan: [docs/KARARSIZIM_PLAN.md](docs/KARARSIZIM_PLAN.md)

**Teknoloji:** Python 3.12 · Django 6.1 · Django şablonları + sade HTML/CSS/JS ·
SQLite (yerel) / Supabase Postgres (production) · Vercel

## Kurulum

Python 3.12 veya üstü gerekir.

```powershell
# 1. Sanal ortam
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate

# 2. Bağımlılıklar
pip install -r requirements.txt -r requirements-dev.txt

# 3. Ortam değişkenleri
copy .env.example .env              # macOS/Linux: cp .env.example .env
# .env içindeki SECRET_KEY için rastgele bir değer üret:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 4. Veritabanı ve yönetici hesabı
python manage.py migrate
python manage.py createsuperuser    # e-posta + kullanıcı adı + parola sorar

# 5. Çalıştır
python manage.py runserver          # http://127.0.0.1:8000
```

## Komutlar

| Ne için | Komut |
|---|---|
| Sunucu | `python manage.py runserver` |
| Test | `python -m pytest` |
| Lint + format | `python -m ruff check . --fix` ve `python -m ruff format .` |
| Sistem kontrolü | `python manage.py check` |
| Deploy kontrolü | `python manage.py check --deploy` |

## Ortam değişkenleri

Hepsi [.env.example](.env.example) içinde açıklanmıştır: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`. `DATABASE_URL` boşsa yerel SQLite (`db.sqlite3`) kullanılır.

## Yayına alma (Supabase + Vercel)

Uygulama Vercel'de, veritabanı Supabase Postgres'te çalışır. Django doğrudan Postgres'e bağlanır;
Supabase'in REST/GraphQL API'si ve JS istemcisi kullanılmaz.

### 1. Supabase

- **Data API'yi kapat** (Project Settings → Data API). Django tabloları `public` şemasında oluşur ve
  Row Level Security kapalıdır; Data API açık kalırsa anon anahtarı olan herkes tabloları (kullanıcılar
  dahil) okuyup değiştirebilir. Güvenlik danışmanında (Advisors → Security) `rls_disabled_in_public`
  uyarısı kalmamalı.
- **Connect** butonundan iki bağlantı dizesi al (`[YOUR-PASSWORD]` yerine veritabanı parolası):
  - **Session pooler**, port **5432**: yerelden migration için.
  - **Transaction pooler**, port **6543**: Vercel çalışma zamanı için.

### 2. Migration (yerelden, session pooler ile)

Transaction pooler migration için uygun değildir. Bağlantı dizesini dosyaya yazma; yalnızca o terminal
oturumunda ortam değişkeni olarak ver:

```powershell
$env:DATABASE_URL = "<session pooler dizesi, port 5432>"
python manage.py migrate
python manage.py createsuperuser     # güçlü ve benzersiz bir parola kullan
Remove-Item Env:DATABASE_URL         # yerel SQLite'a geri dön
```

Her model değişikliğinde: yerelde `makemigrations` → commit → yukarıdaki `migrate` → `git push`.

### 3. Vercel

**Add New → Project** ile GitHub reposunu seç; framework olarak Django algılanmalıdır
(`config.wsgi.application` + `.python-version` ile Python 3.12). **Environment Variables:**

| Değişken | Değer |
|---|---|
| `SECRET_KEY` | Yeni rastgele değer (yereldekinden farklı). Tanımsızsa uygulama Vercel'de başlamaz |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.vercel.app` (özel alan adı eklersen onu da virgülle ekle) |
| `CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app` (özel alan adı için `https://alanadi.com`) |
| `DATABASE_URL` | Supabase **transaction pooler** (port **6543**) dizesi |

Port `6543` algılanınca ayarlar otomatik olarak server-side cursor'ları ve psycopg'nin hazırlanmış
ifadelerini (prepared statements) kapatır; transaction pooler ikisini de desteklemez.

### Deploy öncesi kontrol

```powershell
python -m ruff check .
python -m pytest
python manage.py makemigrations --check --dry-run
```

`check --deploy` için ortamı production gibi kur (güçlü bir `SECRET_KEY` ve `DEBUG=False` ile):
`HSTS` (`security.W004`) ve `SSL redirect` (`security.W008`) uyarıları beklenir. Vercel HTTPS'i zaten
zorunlu tutar, yönlendirme bilerek kapalıdır.

Sorun giderme tablosu için [docs/KARARSIZIM_PLAN.md](docs/KARARSIZIM_PLAN.md) Bölüm 9'a bak.

## Kötüye kullanım koruması (hız sınırları)

Oy, kayıt, giriş ve anket oluşturma sınırlıdır. Sayaçlar bellekte değil `abuse_hit` tablosunda tutulur
(Vercel serverless olduğu için bellek istekler arasında paylaşılmaz). Sınırlar tek yerde:
[abuse/rules.py](abuse/rules.py).

| Ne | Sınır (ilk değerler) |
|---|---|
| Oy (üye veya misafir) | IP + tarayıcı başına dakikada 40, saatte 400 |
| Misafir oyu | Anket başına IP + tarayıcı başına 24 saatte 10 (yalnızca başarılı oylar) |
| Kayıt | IP başına saatte 10 deneme |
| Giriş (site ve `/admin/`) | IP başına dakikada 20 ve saatte 200; e-posta başına 15 dakikada 10 **başarısız** deneme (dolunca doğru parola bile denenmez; e-posta Django'nun kimlik doğrulamasıyla aynı biçimde normalize edilir, Unicode varyantlarıyla atlatılamaz) |
| Anket oluşturma | Kullanıcı başına saatte 10 |

- **Kayıt formu** ayrıca gizli bir tuzak alanı (`hp_alan`) ve imzalı zaman damgası içerir: tuzak doluysa, form 2 saniyeden
  hızlı ya da 2 saatten eski gönderilirse kayıt reddedilir. Harici servis (CAPTCHA) yoktur.
- **Gizlilik:** ham IP, e-posta ya da kullanıcı kimliği saklanmaz; yalnızca `SECRET_KEY`'den türetilmiş anahtarla HMAC-SHA256
  özeti tutulur (IPv6 için /64 öneki). Kayıtlar en geç 25 saat sonra silinir.
- **IP kaynağı:** Vercel'de `x-vercel-forwarded-for` / `x-forwarded-for` başlığı (Vercel dış IP'leri iletmez, sahteciliğe kapalı).
  Başka ortamlarda bu başlıklar yok sayılır, `REMOTE_ADDR` kullanılır. Vercel'de başlık okunamazsa IP'ye bağlı sınırlar atlanır
  (herkes tek kovaya düşmesin diye).
- **Acil durum anahtarı:** sınırlar gerçek kullanıcıları engelliyorsa Vercel'de `RATE_LIMITS_ENABLED=False` yapıp yeniden deploy et.
- **Koruma siteyi çökertmez:** veritabanı hatasında sınırlayıcı loglar ve isteğe izin verir.
- **Üretime alma sırası:** yeni tablo gerektirir. `abuse` migration'ını üretime (session pooler ile, yukarıdaki "Migration"
  bölümü) **deploy'dan ÖNCE** uygula; tablo yokken koruma sessizce devre dışı kalır (site çalışır, sınır uygulanmaz).
- Reddedilen isteklere HTTP 429 ve `Retry-After` başlığı döner. Engelleme olayları (`kapsam`, bekleme süresi; IP yok)
  uygulama günlüğüne yazılır.
