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
