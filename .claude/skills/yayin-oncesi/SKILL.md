---
name: yayin-oncesi
description: Vercel'e deploy etmeden önce kontrol listesini çalıştırır
disable-model-invocation: true
---

Sırayla çalıştır ve her birinin sonucunu raporla:
1. `python -m ruff check .`
2. `python -m pytest`
3. `python manage.py makemigrations --check --dry-run` (eksik migration var mı?)
4. `DEBUG=False python manage.py check --deploy` (uyarıları açıkla)
5. requirements.txt kodda import edilen tüm paketleri içeriyor mu?
6. `.env.example` settings.py'nin okuduğu tüm ortam değişkenlerini listeliyor mu?
7. Şablonlarda e-posta adresi gösterilen bir yer var mı? (grep: "email")
8. `.gitignore` içinde .env, .venv, db.sqlite3, staticfiles var mı?
Sonunda "Deploy'a hazır ✅" veya düzeltilmesi gerekenlerin listesini ver.
