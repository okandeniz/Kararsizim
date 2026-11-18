# kararsızım: Claude Code Geliştirme Planı ve Faz Prompt'ları

> **Bu dosya ne işe yarar?** "kararsızım" prototipini Claude Code ile adım adım geliştirmen için gereken her şey burada: teknik kararlar, veri modeli, tasarım sistemi, Claude Code yapılandırması (CLAUDE.md, izinler, hook'lar, alt ajan, skill'ler, MCP sunucuları) ve **kopyala-yapıştır hazır, fazlara bölünmüş prompt'lar**.
>
> **Nasıl kullanılır?**
> 1. Proje klasörünü oluştur ve bu dosyayı `docs/KARARSIZIM_PLAN.md` olarak içine koy.
> 2. Bölüm 2'deki hazırlıkları yap.
> 3. Fazları sırayla uygula. Bir sonraki faza geçmeden önce her fazın kabul kriterlerini kontrol et.
>
> *Kasım 2026 itibarıyla güncel bilgilerle hazırlandı. Genel Claude Code özellikleri için ayrıca `claude-code-web-gelistirme-rehberi.md` dosyasına bakabilirsin.*

---

## İçindekiler

1. [Proje özeti ve teknik kararlar](#1-proje-özeti-ve-teknik-kararlar)
2. [Ön hazırlık (bir kerelik)](#2-ön-hazırlık-bir-kerelik)
3. [Claude Code yapılandırması](#3-claude-code-yapılandırması)
4. [Veri modeli](#4-veri-modeli)
5. [Sayfalar ve URL haritası](#5-sayfalar-ve-url-haritası)
6. [Tasarım sistemi](#6-tasarım-sistemi)
7. [Çalışma ritmi: her faz nasıl yürütülür?](#7-çalışma-ritmi-her-faz-nasıl-yürütülür)
8. [Fazlar ve prompt'lar](#8-fazlar-ve-promptlar)
   - [Faz 0: Claude Code ortamını kur](#faz-0-claude-code-ortamını-kur)
   - [Faz 1: Django iskeleti ve özel kullanıcı modeli](#faz-1-django-iskeleti-ve-özel-kullanıcı-modeli)
   - [Faz 2: Üyelik (kayıt, giriş, çıkış)](#faz-2-üyelik-kayıt-giriş-çıkış)
   - [Faz 3: Anket oluşturma](#faz-3-anket-oluşturma)
   - [Faz 4: Anket akışı ve oylama](#faz-4-anket-akışı-ve-oylama)
   - [Faz 5: Supabase ve Vercel ile yayına alma](#faz-5-supabase-ve-vercel-ile-yayına-alma)
   - [Faz 6: Arayüz cilası ve uçtan uca test](#faz-6-arayüz-cilası-ve-uçtan-uca-test)
   - [Faz 7 ve sonrası: yol haritası](#faz-7-ve-sonrası-yol-haritası)
9. [Sorun giderme](#9-sorun-giderme)
10. [Kaynaklar](#10-kaynaklar)

---

## 1. Proje özeti ve teknik kararlar

### Ürün tanımı
**kararsızım**, kullanıcıların kararsız kaldıkları konularda ("Bugün sinemaya mı gitsem, restorana mı?") anket açıp diğer kullanıcılara danıştığı bir platformdur.

| Kural | Açıklama |
|---|---|
| Anket yapısı | 1 soru + **en az 2, en fazla 5** seçenek |
| Görünürlük | Herkes platformdaki **tüm** anketleri görür. Takip mekanizması yok |
| Oylama | Üye olan da olmayan da oy verebilir. **Her anket için kişi başı 1 oy** |
| Anket oluşturma | Yalnızca **üyeler** |
| Kayıt | E-posta + parola + **kullanıcı adı** |
| Gizlilik | Anketlerde **yalnızca kullanıcı adı** görünür. **E-posta asla görünmez** |
| Hedef kitle | Gençler: açık arka plan, canlı renklerle tonlanmış, temiz arayüz |
| Hedef | Önce çalışan bir **prototip**, sonra adım adım geliştirme |

### Teknik kararlar

| Konu | Karar | Neden |
|---|---|---|
| Dil / framework | **Python 3.12 + Django 6.1** | Django 6.1 güncel sürüm (Ağustos 2026). Python 3.12–3.14 destekler |
| Frontend | Django şablonları + **sade HTML, CSS, JavaScript** (aynı repo) | Build adımı yok, npm yok. Prototip için en basit yol |
| JS yaklaşımı | **Progressive enhancement**: formlar JS olmadan da çalışır, JS sayfa yenilemeden oy vermeyi sağlar | Sağlam ve basit |
| Kimlik doğrulama | **Django'nun kendi auth sistemi** + özel kullanıcı modeli (e-posta ile giriş) | Supabase Auth'a gerek yok. Tek sistem, daha az karmaşıklık |
| Veritabanı | **Supabase Postgres** (yalnızca veritabanı olarak). Yerel geliştirmede SQLite | Supabase'in JS istemcisi ve REST API'si kullanılmaz. Django doğrudan Postgres'e bağlanır |
| DB bağlantısı (Vercel) | Supabase **transaction pooler (port 6543)** + `DISABLE_SERVER_SIDE_CURSORS=True` + `CONN_MAX_AGE=0` | Serverless ortam çok sayıda kısa ömürlü bağlantı açar |
| Migration | Yerelden **session pooler (port 5432)** üzerinden elle | Transaction pooler migration için uygun değil |
| Deploy | **Vercel** (Django'yu sıfır yapılandırmayla destekliyor) | `manage.py` otomatik algılanır, `collectstatic` otomatik çalışır, statik dosyalar CDN'den sunulur |
| Anonim oy takibi | İmzalı çerez (`voter_id`, UUID, 1 yıl) + veritabanında benzersizlik kısıtı | Basit ve yeterli. Kötüye kullanım önlemleri sonraki fazlarda |
| Statik dosyalar | `static/css/app.css`, `static/js/app.js` | Tek CSS, tek JS dosyası |
| Test | `pytest` + `pytest-django` | Hızlı ve okunaklı |
| Kod kalitesi | `ruff` (format + lint), hook ile otomatik | Claude'un yazdığı kod her zaman formatlı olur |
| Dil | Arayüz metinleri **Türkçe**, kod (değişken, fonksiyon, model adları) **İngilizce** | Standart pratik |

### Prototip kapsamı dışında (sonraki fazlara bırakıldı)
Parola sıfırlama e-postası, oy değiştirme, anket silme/düzenleme, profil sayfası, arama, kategori, yorum, bildirim, görsel yükleme, rate limiting / bot koruması, moderasyon paneli (Django admin dışında).

---

## 2. Ön hazırlık (bir kerelik)

### Hesaplar
- [ ] **Claude** Pro, Max, Team veya Enterprise hesabı (Claude Code için gerekli)
- [ ] **GitHub** hesabı (Vercel deploy için repo)
- [ ] **Supabase** hesabı (Faz 5'te proje oluşturulacak)
- [ ] **Vercel** hesabı (GitHub ile giriş önerilir)

### Bilgisayarına kurulacaklar
```bash
# Python 3.12+ (python.org veya paket yöneticisi)
python --version

# Git
git --version

# Claude Code
curl -fsSL https://claude.ai/install.sh | bash      # macOS / Linux / WSL
# irm https://claude.ai/install.ps1 | iex           # Windows PowerShell
claude --version

# Node.js 20+ (yalnızca npx ile çalışan MCP sunucuları için: Playwright, Context7)
node --version

# Vercel CLI (isteğe bağlı, Faz 5'te işe yarar; sürüm 50.38+ olmalı)
npm install -g vercel
```

### Proje klasörü
```bash
mkdir kararsizim && cd kararsizim
git init
mkdir docs
# Bu dosyayı docs/KARARSIZIM_PLAN.md olarak kaydet

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

claude                              # venv aktifken başlat (hook'lar ruff'ı bulabilsin)
```

> **Önemli:** Claude Code'u her zaman **sanal ortam (venv) aktifken** başlat. Böylece hook'lar ve Claude'un çalıştırdığı `python`, `pytest`, `ruff` komutları doğru ortamı kullanır.

---

## 3. Claude Code yapılandırması

Bu bölümdeki dosyaları **Faz 0'da Claude kendisi oluşturacak**. Burada referans olarak duruyorlar.

### 3.1 Hedef dizin yapısı (Faz 1 sonunda)

```text
kararsizim/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .env.example                 # örnek ortam değişkenleri (commit edilir)
├── .env                         # gerçek değerler (commit EDİLMEZ, sen oluşturursun)
├── .mcp.json                    # proje MCP sunucuları
├── .python-version              # 3.12
├── pyproject.toml               # ruff + pytest ayarları, requires-python
├── requirements.txt             # production bağımlılıkları
├── requirements-dev.txt         # pytest, ruff
├── manage.py
├── config/                      # Django proje modülü
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                    # özel kullanıcı modeli, kayıt/giriş
├── polls/                       # anket, seçenek, oy
├── templates/
│   ├── base.html
│   ├── accounts/
│   └── polls/
├── static/
│   ├── css/app.css
│   ├── js/app.js
│   └── img/
├── docs/
│   └── KARARSIZIM_PLAN.md
└── .claude/
    ├── settings.json
    ├── hooks/
    │   ├── ruff_fix.py
    │   └── django_check.py
    ├── agents/
    │   └── django-reviewer.md
    └── skills/
        ├── faz/SKILL.md
        ├── ui-kontrol/SKILL.md
        └── yayin-oncesi/SKILL.md
```

### 3.2 `CLAUDE.md` (proje kökü)

```markdown
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

## Komutlar
- Sunucu: `python manage.py runserver` → http://127.0.0.1:8000
- Migration: `python manage.py makemigrations && python manage.py migrate`
- Test: `python -m pytest`
- Lint/format: `ruff check . --fix && ruff format .`
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
```

### 3.3 `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(python manage.py *)",
      "Bash(python -m pytest *)",
      "Bash(python -m pytest)",
      "Bash(pytest *)",
      "Bash(ruff *)",
      "Bash(pip install -r requirements.txt)",
      "Bash(pip install -r requirements-dev.txt)",
      "Bash(pip list *)",
      "Bash(git status *)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git add *)",
      "Bash(git commit *)"
    ],
    "ask": [
      "Bash(pip install *)",
      "Bash(git push *)",
      "Bash(vercel *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.local)",
      "Edit(./.env)",
      "Edit(./.env.local)",
      "Bash(cat .env*)",
      "Bash(rm -rf *)"
    ],
    "defaultMode": "acceptEdits"
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/ruff_fix.py\"",
            "timeout": 60
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/django_check.py\"",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

### 3.4 Hook script'leri (Python ile yazıldı, Windows/macOS/Linux'ta çalışır)

`.claude/hooks/ruff_fix.py`: Claude bir `.py` dosyasını düzenleyince ruff ile formatlar ve düzeltir. Kalan lint hatalarını Claude'a geri bildirir.

```python
#!/usr/bin/env python
import json
import shutil
import subprocess
import sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path", "")

if not path.endswith(".py") or shutil.which("ruff") is None:
    sys.exit(0)

subprocess.run(["ruff", "format", path], capture_output=True)
subprocess.run(["ruff", "check", "--fix", path], capture_output=True)
result = subprocess.run(["ruff", "check", path], capture_output=True, text=True)

if result.returncode != 0:
    print(f"ruff sorunları ({path}):\n{result.stdout}", file=sys.stderr)
    sys.exit(2)  # Claude hatayı görür ve düzeltir
sys.exit(0)
```

`.claude/hooks/django_check.py`: Claude bitirmeden önce `manage.py check` çalıştırır. Hata varsa bitirmesine izin vermez.

```python
#!/usr/bin/env python
import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
if data.get("stop_hook_active"):  # sonsuz döngüyü önle
    sys.exit(0)

project = os.environ.get("CLAUDE_PROJECT_DIR", ".")
if not os.path.exists(os.path.join(project, "manage.py")):
    sys.exit(0)  # Django projesi henüz oluşturulmadı

result = subprocess.run(
    [sys.executable, "manage.py", "check"],
    cwd=project, capture_output=True, text=True,
)
if result.returncode != 0:
    print("`python manage.py check` başarısız. Bitirmeden önce düzelt:\n"
          + result.stderr[-3000:], file=sys.stderr)
    sys.exit(2)
sys.exit(0)
```

### 3.5 Alt ajan: `.claude/agents/django-reviewer.md`

```markdown
---
name: django-reviewer
description: kararsızım projesinde değişen kodu güvenlik, gizlilik, doğruluk ve performans açısından inceler. Her fazın sonunda veya kullanıcı inceleme istediğinde kullan.
tools: Read, Grep, Glob, Bash
model: sonnet
memory: project
color: purple
---

Kıdemli bir Django geliştiricisi olarak `git diff` ve değişen dosyaları incele.
Özellikle şunları kontrol et:

GİZLİLİK
- E-posta adresi herhangi bir şablonda, JSON yanıtında, hata mesajında veya
  log çıktısında görünüyor mu? (`user.email`, `{{ user }}`: __str__ e-posta döndürüyor olabilir!)

GÜVENLİK
- POST formlarında csrf_token var mı? fetch istekleri X-CSRFToken gönderiyor mu?
- `|safe`, `mark_safe`, `autoescape off` kullanımı var mı?
- Anket oluşturma `login_required` ile korunuyor mu?
- Seçeneğin gerçekten o ankete ait olduğu doğrulanıyor mu?
- Gizli bilgiler koda gömülmüş mü?

DOĞRULUK
- 2–5 seçenek, boş/tekrarlı seçenek ve uzunluk kontrolleri sunucu tarafında var mı?
- Tek oy kuralı veritabanı kısıtıyla korunuyor mu? IntegrityError düzgün yakalanıyor mu?

PERFORMANS
- Akış sayfasında N+1 sorgusu var mı? (her kart için ayrı sorgu)

Her bulgu için: dosya:satır, sorun, önem (kritik/orta/düşük), somut düzeltme.
Bulgu yoksa açıkça "sorun bulunamadı" de. Tekrarlayan sorunları hafızana kaydet.
```

### 3.6 Skill'ler

`.claude/skills/faz/SKILL.md`: `/faz 3` gibi bir komutla plandaki fazı uygular.

```markdown
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
```

`.claude/skills/ui-kontrol/SKILL.md`: Arayüzü tarayıcıda açıp tasarım sistemine uygunluğunu kontrol eder.

```markdown
---
name: ui-kontrol
description: Çalışan uygulamayı tarayıcıda açıp arayüzü tasarım sistemine göre kontrol eder. Arayüz değişikliklerinden sonra kullan.
argument-hint: "[sayfa-yolu, ör. / veya /anket/yeni/]"
---

1. Sunucu çalışmıyorsa `python manage.py runserver` ile arka planda başlat.
2. Tarayıcı aracıyla (Claude in Chrome veya Playwright MCP) http://127.0.0.1:8000$ARGUMENTS
   sayfasını aç. Sayfa yolu verilmediyse /, /anket/yeni/, /kayit/ ve bir anket detayını gez.
3. Her sayfayı 390px (mobil) ve 1280px (masaüstü) genişlikte kontrol et.
4. docs/KARARSIZIM_PLAN.md "6. Tasarım sistemi" bölümüne göre değerlendir:
   renkler, boşluklar, köşe yuvarlaklığı, okunabilirlik, odak (focus) stilleri, taşmalar.
5. Konsolda JS hatası var mı bak.
6. Sorunları listele ve düzelt. Ardından tekrar kontrol et.
```

`.claude/skills/yayin-oncesi/SKILL.md`: Deploy öncesi kontrol listesi.

```markdown
---
name: yayin-oncesi
description: Vercel'e deploy etmeden önce kontrol listesini çalıştırır
disable-model-invocation: true
---

Sırayla çalıştır ve her birinin sonucunu raporla:
1. `ruff check .`
2. `python -m pytest`
3. `python manage.py makemigrations --check --dry-run` (eksik migration var mı?)
4. `DEBUG=False python manage.py check --deploy` (uyarıları açıkla)
5. requirements.txt kodda import edilen tüm paketleri içeriyor mu?
6. `.env.example` settings.py'nin okuduğu tüm ortam değişkenlerini listeliyor mu?
7. Şablonlarda e-posta adresi gösterilen bir yer var mı? (grep: "email")
8. `.gitignore` içinde .env, .venv, db.sqlite3, staticfiles var mı?
Sonunda "Deploy'a hazır ✅" veya düzeltilmesi gerekenlerin listesini ver.
```

### 3.7 MCP sunucuları

| Sunucu | Ne zaman | Ne için |
|---|---|---|
| **Context7** | Faz 0'dan itibaren | Django 6.1 ve diğer kütüphanelerin güncel dokümantasyonu |
| **Playwright** | Faz 4 ve 6 | Arayüzü gerçek tarayıcıda test etme (izole, oturum bilgisi yok) |
| **Claude in Chrome** (alternatif) | Faz 4 ve 6 | Kendi Chrome'unda test, konsol hatalarını okuma. `claude --chrome` ile başlatılır |
| **Supabase** | Faz 5 | Tabloları inceleme, güvenlik uyarıları (advisors), loglar. **Salt okunur** modda |
| **Vercel** | Faz 5 | Deployment durumu, build ve runtime logları |

Kurulum komutları (Faz 0 ve Faz 5'te kullanılacak):

```bash
# Faz 0
claude mcp add --scope project --transport http context7 https://mcp.context7.com/mcp
claude mcp add --scope project playwright -- npx @playwright/mcp@latest

# Faz 5 (Supabase proje referansını Supabase panelinden al)
claude mcp add --scope project --transport http supabase "https://mcp.supabase.com/mcp?project_ref=PROJE_REF&read_only=true"
claude mcp add --scope project --transport http vercel https://mcp.vercel.com
```

Ekleme sonrası Claude Code içinde `/mcp` yazıp OAuth girişlerini tamamla.

---

## 4. Veri modeli

```text
User (accounts)                Poll (polls)                 Option (polls)
──────────────                 ────────────                 ──────────────
id                             id                           id
email  (benzersiz, gizli)      author → User                poll → Poll
username (benzersiz, görünür)  question (≤ 200)             text (≤ 80)
password                       created_at                   position (0–4)
date_joined

Vote (polls)
────────────
id
poll   → Poll
option → Option
user   → User   (null olabilir: anonim oy)
voter_token     (UUID, null olabilir: üye oyu)
created_at
```

### Model ayrıntıları

**`accounts.User`** (`AbstractUser`'dan türetilir)
- `email`: `EmailField(unique=True)`. Kaydedilirken küçük harfe çevrilir. **Giriş alanı:** `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = ["username"]`
- `username`: 3–20 karakter, yalnızca `a-z A-Z 0-9 _`. Büyük/küçük harf duyarsız benzersiz (`UniqueConstraint(Lower("username"))`). Yasaklı adlar: `admin`, `kararsizim`, `anket`, `kayit`, `giris`, `cikis`, `api`, `static`
- `__str__` **kullanıcı adını** döndürür (e-postayı değil!)

**`polls.Poll`**
- `author`: `ForeignKey(User, on_delete=CASCADE, related_name="polls")`
- `question`: `CharField(max_length=200)`. Boş olamaz, baştaki/sondaki boşluklar kırpılır
- `created_at`: `DateTimeField(auto_now_add=True, db_index=True)`
- Varsayılan sıralama: en yeni önce

**`polls.Option`**
- `poll`: `ForeignKey(Poll, on_delete=CASCADE, related_name="options")`
- `text`: `CharField(max_length=80)`
- `position`: `PositiveSmallIntegerField()` (0–4)
- Kısıt: `UniqueConstraint(fields=["poll", "position"])`. Sıralama: `position`

**`polls.Vote`**
- `poll`: `ForeignKey(Poll, on_delete=CASCADE, related_name="votes")`
- `option`: `ForeignKey(Option, on_delete=CASCADE, related_name="votes")`
- `user`: `ForeignKey(User, null=True, blank=True, on_delete=CASCADE)`
- `voter_token`: `UUIDField(null=True, blank=True)`
- `created_at`: `DateTimeField(auto_now_add=True)`
- Kısıtlar:
  ```python
  constraints = [
      models.UniqueConstraint(
          fields=["poll", "user"],
          condition=models.Q(user__isnull=False),
          name="unique_vote_per_user",
      ),
      models.UniqueConstraint(
          fields=["poll", "voter_token"],
          condition=models.Q(voter_token__isnull=False),
          name="unique_vote_per_token",
      ),
      models.CheckConstraint(
          condition=models.Q(user__isnull=False) | models.Q(voter_token__isnull=False),
          name="vote_has_voter",
      ),
  ]
  ```

### Oy verme kuralları
1. **Üye ise** oy `user` alanıyla kaydedilir.
2. **Anonim ise** imzalı çerezdeki `voter_id` (UUID) okunur. Yoksa yeni UUID üretilip çereze yazılır (`set_signed_cookie`, 1 yıl, `httponly`, `samesite=Lax`, production'da `secure`).
3. Seçeneğin o ankete ait olduğu doğrulanır.
4. Kayıt `transaction.atomic()` içinde yapılır. `IntegrityError` yakalanırsa "Bu ankete zaten oy verdin" mesajı gösterilir.
5. Oy verildikten sonra o kullanıcıya sonuçlar (yüzde + oy sayısı) gösterilir. **Oy değiştirme prototipte yok.**
6. Kendi anketine oy vermek serbesttir.

> **Bilinen prototip sınırlaması:** Anonim oy veren biri sonra giriş yaparsa aynı ankete bir kez daha oy verebilir. Çerezi silen anonim kullanıcı da tekrar oy verebilir. Prototip için kabul edilebilir. Sağlamlaştırma Faz 7+ yol haritasında.

---

## 5. Sayfalar ve URL haritası

| URL | Ad | Erişim | Açıklama |
|---|---|---|---|
| `/` | `polls:feed` | Herkes | Tüm anketler, en yeni önce, sayfa başına 20 (`?page=2`). Kartlarda doğrudan oy verilebilir |
| `/anket/<id>/` | `polls:detail` | Herkes | Tek anket (paylaşılabilir bağlantı). Oy formu veya sonuçlar |
| `/anket/<id>/oy/` | `polls:vote` | Herkes, yalnızca POST | Oy kaydeder. Normal form → yönlendirme. fetch isteği → sonuç HTML parçası döner |
| `/anket/yeni/` | `polls:create` | **Yalnızca üyeler** | Anket oluşturma formu. Üye değilse girişe yönlendirir (`?next=`) |
| `/kayit/` | `accounts:register` | Misafir | Kullanıcı adı + e-posta + parola (x2) |
| `/giris/` | `accounts:login` | Misafir | E-posta + parola |
| `/cikis/` | `accounts:logout` | Üye, yalnızca POST | Çıkış |
| `/admin/` | Django admin | Süper kullanıcı | Moderasyon (anket/oy silme) |

### Şablon parçaları
- `templates/base.html`: header (logo, "Anket oluştur" butonu, giriş/kayıt veya `@kullaniciadi` + çıkış), mesajlar (Django messages), içerik, footer
- `templates/polls/_poll_card.html`: anket kartı. İki durumu var: **oy formu** (henüz oy vermediyse) ve **sonuçlar** (oy verdiyse)
- `templates/polls/_poll_results.html`: sonuç çubukları (fetch yanıtı olarak da döner)

### Oy verme akışı (progressive enhancement)
```text
[Kart: seçenek butonları]  ──(JS yoksa)──▶ POST /anket/5/oy/ ──▶ 302 → geri dön (next)
          │
          └──(JS varsa)──▶ fetch POST /anket/5/oy/ (X-Requested-With: fetch)
                                   └──▶ 200 + _poll_results.html parçası
                                         └──▶ JS kartın içeriğini değiştirir, çubuklar animasyonla dolar
```

---

## 6. Tasarım sistemi

**Hedef his:** Genç, enerjik ama temiz. Açık arka plan, canlı renklerin pastel tonlarıyla boyanmış kartlar, bol boşluk, yuvarlak köşeler. Renk "bağırmasın", tonlarla dolsun.

### Renk token'ları (`static/css/app.css` → `:root`)

```css
:root {
  /* Zemin ve metin */
  --bg: #FAF8FF;            /* çok açık lavanta-beyaz */
  --surface: #FFFFFF;
  --text: #1E1B2E;          /* neredeyse siyah, mor alt tonlu */
  --muted: #6B6880;
  --border: #ECE8F7;

  /* Ana marka */
  --primary: #7C3AED;       /* canlı mor */
  --primary-hover: #6D28D9;
  --primary-tint: #F1EAFE;

  /* Seçenek renkleri: her seçenek sırasına göre bir renk alır (dolu + ton) */
  --c1: #7C3AED; --c1-tint: #F1EAFE;   /* mor */
  --c2: #FF4D8D; --c2-tint: #FFE8F0;   /* pembe */
  --c3: #FF8A3D; --c3-tint: #FFF0E5;   /* turuncu */
  --c4: #14B8A6; --c4-tint: #E3F8F5;   /* turkuaz */
  --c5: #3D8BFF; --c5-tint: #E6F0FF;   /* mavi */

  /* Durum */
  --success: #16A34A;
  --danger: #E11D48;

  /* İmza gradyanı: logo, ana buton ve vurgu alanlarında, ölçülü kullan */
  --gradient: linear-gradient(135deg, #7C3AED 0%, #FF4D8D 55%, #FF8A3D 100%);

  /* Şekil */
  --radius-sm: 10px;
  --radius: 16px;
  --radius-lg: 24px;
  --radius-pill: 999px;
  --shadow: 0 6px 20px rgba(124, 58, 237, 0.08);
  --shadow-hover: 0 10px 28px rgba(124, 58, 237, 0.16);

  /* Boşluk ölçeği */
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 24px; --s6: 32px; --s7: 48px;

  /* Tipografi */
  --font: "Plus Jakarta Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
}
```

### Tipografi
- Font: **Plus Jakarta Sans** (Google Fonts; 400, 600, 800). Türkçe karakterleri destekler
- Soru başlıkları: 1.25rem, 800 kalınlık. Gövde: 1rem, 400. Küçük metinler (`@kullanici · 3 saat önce`): 0.875rem, `--muted`
- Logo: "kararsızım" küçük harf, 800 kalınlık, metin rengi `--gradient` (`background-clip: text`)

### Bileşenler
| Bileşen | Stil |
|---|---|
| **Sayfa düzeni** | Mobil öncelikli. İçerik sütunu en fazla 640px, ortalanmış. Header yapışkan (sticky), beyaz, alt kenarlık |
| **Anket kartı** | `--surface` zemin, `--radius-lg`, `--shadow`, 24px iç boşluk. Üstte `@kullaniciadi · zaman`, sonra soru, sonra seçenekler, altta "N oy" |
| **Seçenek butonu (oy öncesi)** | Tam genişlik, `--radius`, zemin seçenek tonu (`--c1-tint`…), sol kenarda 4px dolu renk şeridi, hover'da hafif büyüme (`scale(1.01)`) ve renk koyulaşması |
| **Sonuç çubuğu (oy sonrası)** | Ton zemin üzerinde dolu renk çubuk, genişlik = yüzde, 600ms animasyonla dolar. Sağda `%42 · 12 oy`. Kullanıcının seçtiği seçenekte ✓ işareti. En çok oy alan seçenek kalın yazılır |
| **Ana buton** | `--gradient` zemin, beyaz metin, `--radius-pill`, 600 kalınlık. Hover'da `--shadow-hover` |
| **İkincil buton** | Beyaz zemin, `--primary` metin, `--border` kenarlık, pill |
| **Form alanları** | 48px yükseklik, `--radius`, `--border` kenarlık. Focus'ta `--primary` kenarlık + 3px `--primary-tint` halka. Hata metni `--danger` ve alanın altında |
| **Mesajlar (toast)** | Üstte, ton zeminli kutu (başarı: yeşil ton, hata: kırmızı ton), birkaç saniye sonra kaybolur |
| **Boş durum** | "Henüz anket yok. İlk kararsızlığı sen paylaş! 🤔" + ana buton |
| **Anket oluşturma** | Soru alanı + seçenek listesi. "+ Seçenek ekle" (5'e kadar), her seçeneğin yanında × (2'nin altına inemez). Seçenek giriş kutusunun sol kenarı o seçeneğin rengini taşır. Kalan karakter sayacı |

### Erişilebilirlik ve detaylar
- Beyaz metni yalnızca koyu/doygun zemin üzerinde kullan. Pastel tonların üstünde `--text` kullan (WCAG AA kontrastı)
- Her etkileşimli öğede görünür `:focus-visible` stili
- `prefers-reduced-motion` açıksa animasyonları kapat
- Dokunma hedefleri en az 44×44px
- Göreli zaman: `django.contrib.humanize` → `naturaltime` ("3 saat önce")

---

## 7. Çalışma ritmi: her faz nasıl yürütülür?

```text
1. /clear                       → temiz bağlamla başla
2. /faz N                       → (veya aşağıdaki prompt'u yapıştır) Claude önce plan sunar
3. Planı oku, gerekirse düzelt  → onayla
4. Claude uygular               → hook'lar format ve kontrolü otomatik yapar
5. Kabul kriterlerini elle dene → tarayıcıda http://127.0.0.1:8000
6. "django-reviewer alt ajanıyla bu fazı incele"
7. git add . && git commit -m "Faz N: ..."
```

**İpuçları**
- Plan modu için `Shift+Tab` ile mod değiştirebilir veya prompt'un başına `/plan` yazabilirsin.
- Claude yanlış yöne giderse `Esc` ile durdur. Geri almak için `Esc Esc` veya `/rewind` kullan.
- Bir şey çalışmıyorsa hatayı ve ekran görüntüsünü doğrudan yapıştır.
- Faz uzadıkça bağlam dolar. `/context` ile kontrol et, gerekirse `/compact` çalıştır.
- Her fazı ayrı bir commit olarak sakla. Bir şey bozulursa geri dönmek kolay olur.

---

## 8. Fazlar ve prompt'lar

---

### Faz 0: Claude Code ortamını kur

**Amaç:** Claude Code'un bu projede doğru çalışması için yapılandırma dosyalarını oluşturmak. Henüz Django kodu yok.

**Senin yapacakların (önce):**
```bash
cd kararsizim
source .venv/bin/activate
claude mcp add --scope project --transport http context7 https://mcp.context7.com/mcp
claude mcp add --scope project playwright -- npx @playwright/mcp@latest
claude
```

**Claude için prompt:**
```text
docs/KARARSIZIM_PLAN.md dosyasındaki "3. Claude Code yapılandırması" bölümünü oku.
Bu fazda YALNIZCA Claude Code yapılandırmasını kuracağız, Django kodu yazmayacağız.

Şunları planda yazdığı gibi oluştur:
1. CLAUDE.md (Bölüm 3.2)
2. .claude/settings.json (Bölüm 3.3)
3. .claude/hooks/ruff_fix.py ve .claude/hooks/django_check.py (Bölüm 3.4)
4. .claude/agents/django-reviewer.md (Bölüm 3.5)
5. .claude/skills/faz/SKILL.md, .claude/skills/ui-kontrol/SKILL.md,
   .claude/skills/yayin-oncesi/SKILL.md (Bölüm 3.6)
6. .gitignore: Python, .venv, .env, .env.local, db.sqlite3, staticfiles/,
   __pycache__, .pytest_cache, .ruff_cache, .vercel, .DS_Store
7. requirements-dev.txt: pytest, pytest-django, ruff. Ardından
   `pip install -r requirements-dev.txt` çalıştır.

Bitince oluşturduğun dosyaları listele ve .mcp.json içeriğini göster.
```

**Kabul kriterleri**
- [ ] Yukarıdaki tüm dosyalar mevcut
- [ ] `ruff --version` çalışıyor
- [ ] `/mcp` komutunda `context7` ve `playwright` görünüyor
- [ ] `/skills` listesinde `faz`, `ui-kontrol`, `yayin-oncesi` var

**Sonra:** Ayarların ve hook'ların yüklenmesi için Claude Code'dan çık (`/exit`) ve yeniden başlat (`claude`).
**Commit:** `Faz 0: Claude Code yapılandırması`

---

### Faz 1: Django iskeleti ve özel kullanıcı modeli

**Amaç:** Çalışan bir Django projesi, ortam değişkenli ayarlar, **özel kullanıcı modeli** (ilk migration'dan önce, sonradan değiştirmek çok zahmetli!), temel şablon ve tasarım token'ları.

**Claude için prompt:**
```text
/faz 1
```
*(Skill kullanmıyorsan aşağıdaki metni doğrudan yapıştır.)*

```text
kararsızım projesinin Django iskeletini kur. Ayrıntılar için
docs/KARARSIZIM_PLAN.md Bölüm 1, 3.1, 4 (yalnızca User) ve 6'ya bak.

1. Bağımlılıklar
   - requirements.txt: Django 6.1.x, psycopg[binary], dj-database-url, python-dotenv
   - pyproject.toml: requires-python = ">=3.12", ruff ayarları (line-length 100,
     isort dahil), pytest ayarları (DJANGO_SETTINGS_MODULE=config.settings)
   - .python-version: 3.12
   - Context7 ile Django 6.1 dokümantasyonunu kontrol ederek güncel API kullan.

2. Proje: `django-admin startproject config .` ve `accounts`, `polls` uygulamaları.

3. config/settings.py (ortam değişkenleriyle)
   - .env dosyasını python-dotenv ile yükle (dosya yoksa sorun çıkmasın)
   - SECRET_KEY, DEBUG (varsayılan False), ALLOWED_HOSTS ve CSRF_TRUSTED_ORIGINS
     (virgülle ayrılmış listeler) ortamdan okunsun
   - DATABASES: DATABASE_URL varsa dj_database_url.parse(url, conn_max_age=0,
     ssl_require=True) kullan; URL ":6543" içeriyorsa (Supabase transaction pooler)
     DISABLE_SERVER_SIDE_CURSORS=True ekle. DATABASE_URL yoksa SQLite (db.sqlite3).
   - LANGUAGE_CODE="tr", TIME_ZONE="Europe/Istanbul", USE_TZ=True
   - AUTH_USER_MODEL="accounts.User"
   - TEMPLATES DIRS=[BASE_DIR/"templates"], STATICFILES_DIRS=[BASE_DIR/"static"],
     STATIC_ROOT=BASE_DIR/"staticfiles", STATIC_URL="/static/"
   - django.contrib.humanize ekli olsun
   - DEBUG False iken: SECURE_PROXY_SSL_HEADER, SESSION_COOKIE_SECURE,
     CSRF_COOKIE_SECURE, SECURE_SSL_REDIRECT=False (Vercel HTTPS'i zaten zorunlu tutuyor)
   - LOGIN_URL="accounts:login", LOGIN_REDIRECT_URL="polls:feed",
     LOGOUT_REDIRECT_URL="polls:feed"

4. accounts.User modeli (Bölüm 4'teki kurallarla)
   - AbstractUser'dan türet; email benzersiz ve giriş alanı (USERNAME_FIELD="email",
     REQUIRED_FIELDS=["username"])
   - username: 3–20 karakter, ^[A-Za-z0-9_]+$ validator, büyük/küçük harf duyarsız
     benzersizlik (UniqueConstraint + Lower), yasaklı adlar listesi
   - email kaydederken küçük harfe çevir; __str__ username döndürsün
   - Gerekirse özel UserManager yaz (create_user/create_superuser e-posta ile çalışsın)
   - Admin'e kaydet (e-posta admin'de görünebilir, sadece public sayfalarda gizli)
   - İlk migration'ı oluştur ve uygula

5. Şablon ve statik dosyalar
   - templates/base.html: Türkçe, responsive meta, Plus Jakarta Sans (Google Fonts),
     sticky header (gradyanlı "kararsızım" logosu, "Anket oluştur" butonu,
     giriş/kayıt bağlantıları — henüz çalışmasalar da URL'leri "#" olabilir),
     Django messages alanı, {% block content %}, footer
   - static/css/app.css: Bölüm 6'daki TÜM token'lar :root içinde; temel reset,
     tipografi, layout (max 640px sütun), buton, kart, form ve mesaj stilleri
   - static/js/app.js: boş iskelet + CSRF token'ı çerezden okuyan getCookie yardımcısı
   - polls uygulamasında geçici bir feed view'ı ("Yakında burada anketler olacak" kartı)
     ve config/urls.py'de "/" adresine bağla (namespace: polls)

6. .env.example: SECRET_KEY, DEBUG=True, ALLOWED_HOSTS=127.0.0.1,localhost,
   CSRF_TRUSTED_ORIGINS=, DATABASE_URL= (boş bırakılırsa SQLite) — açıklamalı yorumlarla

7. Testler: tests/ veya her uygulamada test dosyası; User oluşturma, e-posta küçük harf,
   username validasyonu, büyük/küçük harf duyarsız benzersizlik, ana sayfa 200 dönüyor.

8. README.md: kurulum adımları (venv, pip install, .env, migrate, runserver, test).

Bitince runserver ile ana sayfanın açıldığını doğrula.
```

**Senin yapacakların (sonra):**
```bash
cp .env.example .env
# .env içinde SECRET_KEY için rastgele bir değer üret:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python manage.py createsuperuser
python manage.py runserver
```

**Kabul kriterleri**
- [ ] http://127.0.0.1:8000 açılıyor; açık zemin, gradyanlı logo, temiz header görünüyor
- [ ] `python manage.py createsuperuser` e-posta + kullanıcı adı soruyor
- [ ] /admin/ adresine e-posta ile giriş yapılabiliyor
- [ ] `python -m pytest` geçiyor
- [ ] `ruff check .` temiz

**Commit:** `Faz 1: Django iskeleti, özel kullanıcı modeli, tasarım token'ları`

---

### Faz 2: Üyelik (kayıt, giriş, çıkış)

**Amaç:** Kullanıcıların kayıt olması, giriş ve çıkış yapması.

**Claude için prompt:**
```text
/faz 2
```
```text
accounts uygulamasında üyelik akışını yap (docs/KARARSIZIM_PLAN.md Bölüm 4, 5, 6).

1. Kayıt (/kayit/, accounts:register)
   - Alanlar: kullanıcı adı, e-posta, parola, parola tekrar
   - UserCreationForm tabanlı özel form; Django'nun parola validator'ları aktif
   - Hata mesajları Türkçe ve alanın altında; "Bu kullanıcı adı alınmış",
     "Bu e-posta ile zaten bir hesap var" gibi net mesajlar
   - Kullanıcı adı alanının altında ipucu: "3–20 karakter; harf, rakam ve _ kullanabilirsin.
     Anketlerde bu ad görünecek."
   - E-posta alanının altında: "E-postan kimseye gösterilmez."
   - Başarılı kayıtta otomatik giriş yap, `next` parametresi varsa (güvenli URL ise)
     oraya, yoksa ana sayfaya yönlendir; "Hoş geldin @kullaniciadi!" mesajı

2. Giriş (/giris/, accounts:login)
   - E-posta + parola; Django LoginView ve AuthenticationForm (alan etiketi "E-posta")
   - Hatalı girişte genel mesaj: "E-posta veya parola hatalı."
   - Altta "Hesabın yok mu? Kayıt ol" bağlantısı (next parametresini koru)

3. Çıkış (/cikis/, accounts:logout): yalnızca POST, header'da küçük form butonu

4. Giriş yapmış kullanıcı /kayit/ veya /giris/ açarsa ana sayfaya yönlendir.

5. Header'ı güncelle: misafirse "Giriş yap" + "Kayıt ol"; üyeyse "@kullaniciadi" + "Çıkış".
   "Anket oluştur" butonu her durumda görünsün (Faz 3'te bağlanacak).

6. Formlar Bölüm 6'daki form stillerini kullansın; kart içinde ortalanmış, mobilde rahat.

7. Testler: başarılı kayıt + otomatik giriş, tekrarlı e-posta/kullanıcı adı (büyük/küçük
   harf farklı da olsa), geçersiz kullanıcı adı, giriş başarılı/başarısız, çıkış POST,
   GET ile çıkışın çalışmaması, sayfalarda e-posta adresinin görünmemesi.
```

**Kabul kriterleri**
- [ ] Yeni hesap açılıyor ve otomatik giriş yapılıyor
- [ ] Aynı kullanıcı adı farklı harf büyüklüğüyle (`Ali` / `ali`) alınamıyor
- [ ] Header'da `@kullaniciadi` görünüyor, **e-posta hiçbir yerde görünmüyor**
- [ ] Çıkış ve tekrar giriş çalışıyor
- [ ] Testler geçiyor

**Sonra:** `django-reviewer alt ajanıyla Faz 2 değişikliklerini incele`
**Commit:** `Faz 2: Kayıt, giriş, çıkış`

---

### Faz 3: Anket oluşturma

**Amaç:** Üyelerin 2–5 seçenekli anket oluşturabilmesi.

**Claude için prompt:**
```text
/faz 3
```
```text
polls uygulamasında anket oluşturmayı yap (docs/KARARSIZIM_PLAN.md Bölüm 4, 5, 6).

1. Modeller: Poll, Option ve Vote'u Bölüm 4'teki alanlar ve kısıtlarla oluştur
   (Vote bu fazda kullanılmayacak ama migration'ı şimdi hazır olsun). Admin'e kaydet:
   Poll admin'de Option'lar inline görünsün, oy sayısı listede olsun.

2. /anket/yeni/ (polls:create), login_required
   - Misafir gelirse giriş sayfasına `?next=/anket/yeni/` ile yönlendir; giriş sayfasında
     "Anket oluşturmak için giriş yapmalısın" mesajı
   - Form: soru (en fazla 200 karakter) + seçenekler
   - Seçenekler HTML'de 5 ayrı input olarak render edilir (name="option"), ilk 2'si zorunlu
     görünür. JS YOKKEN 5 alanın hepsi görünür, boş olanlar yok sayılır.
   - JS VARKEN: boş fazla alanlar gizlenir, "+ Seçenek ekle" butonu (5'e ulaşınca gizlenir),
     her seçeneğin yanında × butonu (2'nin altına inmez), soru ve seçeneklerde kalan
     karakter sayacı. Her seçenek kutusunun sol kenarı sırasına göre --c1…--c5 rengini alır.

3. Sunucu tarafı doğrulama (forms.py, view'da değil)
   - Soru boş olamaz, kırpılır, ≤ 200
   - Seçenekler: kırp, boşları at, 2 ≤ adet ≤ 5, her biri ≤ 80, büyük/küçük harf duyarsız
     tekrarlı seçenek olamaz ("Aynı seçeneği iki kez yazdın")
   - Hatalarda girilen değerler korunarak form tekrar gösterilsin

4. Kaydetme: transaction.atomic içinde Poll + Option'lar (position 0..n-1).
   Başarıda "Anketin yayında! 🎉" mesajı ve anketin detay sayfasına yönlendirme.
   Detay sayfası (/anket/<id>/, polls:detail) bu fazda basit olabilir: soru, @yazar,
   zaman (naturaltime), seçenek listesi. Oylama Faz 4'te.

5. Header'daki "Anket oluştur" butonunu bağla.

6. Testler: misafir yönlendirmesi, 1 seçenekle hata, 6 seçenekle hata (POST manipülasyonu),
   tekrarlı seçenek hatası, boş soru, 80+ karakter seçenek, başarılı oluşturma
   (2 ve 5 seçenekle), position sırası, yazarın doğru atanması.
```

**Kabul kriterleri**
- [ ] Misafir "Anket oluştur"a basınca girişe yönleniyor, giriş sonrası forma dönüyor
- [ ] 2–5 seçenekle anket oluşturulabiliyor; 1 veya tekrarlı seçenekle hata veriyor
- [ ] JS kapalıyken (tarayıcı geliştirici araçlarından) form yine çalışıyor
- [ ] Detay sayfasında `@kullaniciadi` görünüyor, e-posta görünmüyor
- [ ] Testler geçiyor

**Commit:** `Faz 3: Anket oluşturma`

---

### Faz 4: Anket akışı ve oylama

**Amaç:** Herkesin tüm anketleri görüp (üye olmadan da) oy verebilmesi. Sonuçların canlı ve renkli gösterilmesi. **Prototipin kalbi bu faz.**

**Claude için prompt:**
```text
/faz 4
```
```text
Anket akışını ve oylamayı yap (docs/KARARSIZIM_PLAN.md Bölüm 4 "Oy verme kuralları",
Bölüm 5 "Oy verme akışı" ve Bölüm 6).

1. Akış (/, polls:feed)
   - Tüm anketler, en yeni önce, Django Paginator ile sayfa başına 20, altta
     "Önceki / Sonraki" bağlantıları
   - Sorgu verimliliği: select_related("author"), toplam oy sayısı annotate(Count),
     seçenekleri oy sayılarıyla Prefetch + annotate. Ziyaretçinin bu sayfadaki anketlerden
     hangilerine oy verdiğini TEK sorguyla bul (user veya voter_token'a göre),
     seçtiği option id'leriyle birlikte. Sayfa başına sabit sayıda sorgu olsun
     (test et: django_assert_max_num_queries).
   - Boş durum kartı (Bölüm 6)

2. Kart parçası: templates/polls/_poll_card.html
   - Üst: @yazar · naturaltime; soru; altta "N oy" ve "Paylaş" (detay bağlantısı)
   - Oy vermediyse: her seçenek bir buton (form içinde, name="option", value=id),
     seçenek renkleri --c1…--c5 (position'a göre)
   - Oy verdiyse: _poll_results.html (yüzde çubukları, kullanıcının seçimi ✓, lider kalın)
   - Akışta ve detay sayfasında aynı parça kullanılsın

3. Oy kaydetme (/anket/<id>/oy/, polls:vote, require_POST)
   - Bölüm 4'teki kurallar: üye → user; anonim → imzalı "voter_id" çerezi
     (yoksa uuid4 üret; set_signed_cookie, salt="kararsizim-voter", 1 yıl, httponly,
     samesite="Lax", secure=not DEBUG)
   - Seçeneğin bu ankete ait olduğunu doğrula (değilse 400)
   - transaction.atomic + IntegrityError → "Bu ankete zaten oy verdin"
   - İstek fetch ise (header "X-Requested-With: fetch"): 200 ile _poll_results.html
     parçasını döndür (hata durumunda 4xx + kısa Türkçe mesaj). Normal form ise:
     messages ile bilgi verip `next` parametresine (güvenliyse) veya detay sayfasına yönlendir.

4. static/js/app.js
   - Oy formlarını yakala (event delegation), fetch ile gönder (X-CSRFToken çerezden),
     butonları geçici devre dışı bırak, gelen HTML'i kartın seçenek alanına koy,
     toplam oy sayısını güncelle
   - Çubuk animasyonu: önce width 0, sonra requestAnimationFrame ile hedef genişlik
     (CSS transition 600ms); prefers-reduced-motion'a saygı
   - Hata olursa kartın içinde küçük bir hata mesajı göster

5. Detay sayfasını (polls:detail) kart parçasını kullanacak şekilde güncelle;
   sayfa başlığı ve meta description anketin sorusu olsun.

6. Testler: anonim oy + çerez oluşması, aynı çerezle ikinci oyun reddi, üye oyu,
   üyenin ikinci oyunun reddi, başka ankete ait option ile 400, GET ile 405,
   fetch isteğine parça HTML dönmesi, yüzde hesapları (0 oyda bölme hatası yok),
   akış sorgu sayısı, sayfalama.
```

**Senin yapacakların (sonra):** Tarayıcıda gizli pencere açıp misafir olarak oy ver; normal pencerede üye olarak oy ver. Birkaç anket oluşturup akışı doldur.

Ardından Claude'a:
```text
/ui-kontrol /
```

**Kabul kriterleri**
- [ ] Üye olmadan akışta oy verilebiliyor, sayfa yenilenmeden sonuçlar animasyonla geliyor
- [ ] Sayfa yenilenince oy verilen ankette sonuçlar görünmeye devam ediyor
- [ ] Aynı tarayıcıdan ikinci oy verilemiyor
- [ ] JS kapalıyken oy verme form gönderimiyle çalışıyor
- [ ] Akış 20'den fazla ankette sayfalanıyor
- [ ] Testler geçiyor

**Sonra:** `django-reviewer alt ajanıyla Faz 3 ve 4'ü incele`
**Commit:** `Faz 4: Akış ve oylama`

> 🎉 Bu noktada **yerelde çalışan bir prototipin** var.

---

### Faz 5: Supabase ve Vercel ile yayına alma

**Amaç:** Uygulamayı Supabase Postgres veritabanıyla Vercel'de yayına almak.

#### 5.1 Senin yapacakların: Supabase

1. [supabase.com](https://supabase.com) → **New project**
   - Ad: `kararsizim`, güçlü bir veritabanı parolası (kaydet!)
   - Bölge: **Central EU (Frankfurt)**, Türkiye'ye en yakın seçenek
   - **Data API'yi kapat** (ya da "Automatically expose new tables" kutusunu işaretleme). Biz Supabase'in REST/GraphQL API'sini kullanmıyoruz. Django doğrudan Postgres'e bağlanıyor. Açık bırakırsan Django'nun oluşturduğu tablolar (kullanıcılar dahil) internete açık bir API'den erişilebilir olabilir. Proje oluştuktan sonra da **Project Settings → Data API** bölümünden kapatabilirsin.
2. Proje panelinde **Connect** butonuna bas ve iki bağlantı dizesini kopyala:
   - **Session pooler** (port **5432**): yerelden migration için
   - **Transaction pooler** (port **6543**): Vercel için
   - `[YOUR-PASSWORD]` kısmını kendi parolanla değiştir.
3. Proje referansını (URL'deki `xxxxxxxx` kısmı) not al.

#### 5.2 Senin yapacakların: veritabanını hazırla
```bash
# .env içinde DATABASE_URL'i GEÇİCİ olarak SESSION pooler (5432) dizesine ayarla
python manage.py migrate
python manage.py createsuperuser
# Sonra yerel geliştirmeye devam etmek için DATABASE_URL'i tekrar boşalt (SQLite)
# ya da Supabase'de kalmak istiyorsan session pooler'ı kullanmaya devam et.
```

#### 5.3 Senin yapacakların: MCP sunucularını ekle
```bash
claude mcp add --scope project --transport http supabase "https://mcp.supabase.com/mcp?project_ref=PROJE_REF&read_only=true"
claude mcp add --scope project --transport http vercel https://mcp.vercel.com
claude
> /mcp     # supabase ve vercel için OAuth girişi yap
```

#### 5.4 Claude için prompt (yayın öncesi hazırlık)
```text
/yayin-oncesi
```
Ardından:
```text
Vercel deploy'una hazırlan (docs/KARARSIZIM_PLAN.md Bölüm 1 "Teknik kararlar").

1. settings.py'yi gözden geçir: DEBUG=False'ta güvenli varsayılanlar, ALLOWED_HOSTS ve
   CSRF_TRUSTED_ORIGINS'in ".vercel.app" ve "https://*.vercel.app" ile çalışabilmesi,
   STATIC_ROOT tanımlı (Vercel collectstatic'i otomatik çalıştırır ve CDN'den sunar),
   transaction pooler (:6543) algılandığında DISABLE_SERVER_SIDE_CURSORS=True.
2. config/wsgi.py'de `application` tanımlı ve WSGI_APPLICATION doğru mu kontrol et.
3. Supabase MCP ile: tabloların oluştuğunu doğrula (list_tables) ve güvenlik
   uyarılarını kontrol et (get_advisors). Uyarı varsa açıkla ve ne yapmam gerektiğini söyle.
4. README'ye "Yayına alma" bölümü ekle: Vercel'de ayarlanacak ortam değişkenleri
   listesi ve migration'ın yerelden session pooler ile çalıştırılacağı notu.
5. Bana Vercel'de girmem gereken ortam değişkenlerinin tam listesini, örnek değerlerle
   (gerçek secret'lar olmadan) ver.
```

#### 5.5 Senin yapacakların: GitHub ve Vercel
```bash
git add . && git commit -m "Faz 5: deploy hazırlığı"
# GitHub'da "kararsizim" adında boş bir repo oluştur, sonra:
git remote add origin https://github.com/KULLANICI_ADIN/kararsizim.git
git push -u origin main
```

Vercel'de:
1. **Add New → Project** → GitHub reposunu seç. Framework olarak Django otomatik algılanmalı.
2. **Environment Variables:**

| Değişken | Değer |
|---|---|
| `SECRET_KEY` | Yeni rastgele değer (yereldekiyle aynı olmasın) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.vercel.app` (özel alan adı eklersen onu da ekle) |
| `CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app` |
| `DATABASE_URL` | Supabase **transaction pooler** (port **6543**) dizesi |

3. **Deploy.** Bitince verilen URL'yi aç.

#### 5.6 Claude için prompt (deploy sonrası kontrol)
```text
Vercel MCP ile son deployment'ın durumunu ve build loglarını kontrol et. Ardından
canlı siteyi Playwright ile aç: ana sayfa, kayıt, giriş, anket oluşturma ve misafir
olarak oy verme akışlarını dene. Runtime loglarında hata varsa nedenini bul ve
düzeltme öner. Bölüm 9 "Sorun giderme" tablosundan faydalan.
```

**Kabul kriterleri**
- [ ] Canlı URL açılıyor, CSS ve JS yükleniyor
- [ ] Canlıda kayıt, giriş, anket oluşturma ve oy verme çalışıyor
- [ ] Veriler Supabase'de görünüyor (Table Editor)
- [ ] Supabase güvenlik danışmanında (advisors) kritik uyarı yok
- [ ] `git push` sonrası Vercel otomatik deploy ediyor

**Commit:** `Faz 5: Supabase + Vercel ile yayında`

> **Bundan sonraki model değişiklikleri için:** Yerelde `makemigrations` çalıştır → commit et → `DATABASE_URL`'i session pooler'a ayarlayıp `migrate` çalıştır → push et.

---

### Faz 6: Arayüz cilası ve uçtan uca test

**Amaç:** Arayüzü "gençlerin ilgisini çeken" seviyeye taşımak, mobil deneyimi mükemmelleştirmek, temel uçtan uca testleri eklemek.

**Claude için prompt:**
```text
/faz 6
```
```text
Arayüzü cilala ve uçtan uca kontrol yap (docs/KARARSIZIM_PLAN.md Bölüm 6).

1. Tasarım tutarlılığı: tüm sayfaları Bölüm 6'ya göre gözden geçir; renk token'ları
   dışında sabit renk kalmasın. Kartlarda hover/press mikro etkileşimleri, oy butonuna
   basınca kısa bir "pop" animasyonu, sonuç gelince liderin hafif vurgulanması.
2. Mobil: 360–430px genişlikte her sayfa kusursuz olsun; sticky header küçük ekranda
   sadeleşsin ("Anket oluştur" yerine "+" ikonlu yuvarlak buton).
3. Boş durumlar, 404 ve 500 şablonları (marka diliyle, eğlenceli kısa metinler).
4. Favicon (SVG, gradyanlı "k" harfi), <title> ve Open Graph meta etiketleri
   (detay sayfasında soru başlık olsun; paylaşınca güzel görünsün).
5. Erişilebilirlik: :focus-visible stilleri, form label'ları, aria-live ile oy sonucu
   duyurusu, kontrast kontrolü, prefers-reduced-motion.
6. /ui-kontrol skill'ini çalıştır: /, /anket/yeni/, /kayit/, /giris/ ve bir detay sayfası;
   390px ve 1280px. Bulduğun sorunları düzelt.
7. Playwright ile bir uçtan uca senaryo çalıştır ve sonucu raporla: kayıt ol → anket
   oluştur (3 seçenek) → çıkış yap → misafir olarak oy ver → sonuçları gör →
   tekrar oy verememeyi doğrula.
8. Son olarak django-reviewer alt ajanıyla tüm kod tabanını incele ve kritik bulguları düzelt.
```

**Kabul kriterleri**
- [ ] Telefonunda canlı siteyi aç: hızlı, okunaklı, renkli ama temiz
- [ ] Bir arkadaşına anket bağlantısı gönder, önizleme güzel görünüyor
- [ ] Uçtan uca senaryo sorunsuz
- [ ] İnceleme ajanı kritik bulgu bildirmiyor

**Commit:** `Faz 6: Arayüz cilası, erişilebilirlik, e2e kontrol` → push → Vercel otomatik deploy

> 🚀 **Prototip tamam!**

---

### Faz 7 ve sonrası: yol haritası

Prototipten sonra öncelik sırasına göre önerilen adımlar. Her birini ayrı bir faz olarak `/plan` ile başlat.

| # | Özellik | Not |
|---|---|---|
| 7 | **Kötüye kullanım koruması** | Oy ve kayıt için rate limiting (ör. IP + çerez başına dakikada N istek), anonim oyda IP hash'i ile ek kontrol, kayıtta bot koruması (Cloudflare Turnstile gibi) |
| 8 | **Oy birleştirme** | Anonim oy verip sonra giriş yapan kullanıcının çerez oylarını hesabına bağla (çifte oyu önler) |
| 9 | **"Benim anketlerim" ve anket silme** | Kullanıcı kendi anketlerini görür ve silebilir |
| 10 | **Sıralama sekmeleri** | "Yeni" / "Popüler (son 24 saat)" / "Oy bekleyenler" |
| 11 | **Parola sıfırlama** | E-posta gönderimi (Resend, Postmark vb. bir servis + Django e-posta backend'i) |
| 12 | **Anket süresi** | İsteğe bağlı bitiş zamanı ("1 saat", "1 gün"); süresi dolan anket oylamaya kapanır |
| 13 | **Oy değiştirme** | Belirli süre içinde oyunu değiştirebilme |
| 14 | **Moderasyon** | Anket bildirme, küfür filtresi, admin'de bildirilen anketler listesi |
| 15 | **Kullanıcı profili** | `/u/<kullaniciadi>/` herkese açık anket listesi (takip yok) |
| 16 | **Canlı sonuçlar** | Detay sayfasında periyodik yenileme (basit polling), ileride WebSocket |
| 17 | **Görseller** | Seçeneklere görsel ekleme (Supabase Storage) |

---

## 9. Sorun giderme

| Belirti | Olası neden | Çözüm |
|---|---|---|
| `DisallowedHost` hatası | Alan adı `ALLOWED_HOSTS`'ta yok | Vercel'de `ALLOWED_HOSTS=.vercel.app` (baştaki nokta tüm alt alan adlarını kapsar) |
| Canlıda form gönderince **CSRF hatası (403)** | `CSRF_TRUSTED_ORIGINS` eksik veya `https://` yok | `CSRF_TRUSTED_ORIGINS=https://*.vercel.app` ve `SECURE_PROXY_SSL_HEADER` ayarlı olmalı |
| Canlıda **CSS/JS yüklenmiyor** | `STATIC_ROOT` tanımlı değil veya şablonda sabit yol var | `STATIC_ROOT` tanımla. Şablonlarda `{% static 'css/app.css' %}` kullan |
| `cursor "_django_curs_..." does not exist` | Transaction pooler + server-side cursor | `DISABLE_SERVER_SIDE_CURSORS=True` (URL `:6543` içeriyorsa otomatik olmalı) |
| `migrate` takılıyor veya bağlanamıyor | Transaction pooler veya IPv6 direkt bağlantı kullanılıyor | Migration için **session pooler (5432)** dizesini kullan |
| `too many connections` | Bağlantılar açık kalıyor | Vercel'de transaction pooler (6543) ve `conn_max_age=0` kullan |
| Supabase'den "RLS disabled in public" e-postası | Data API açık, tablolar REST API'ye açık | **Project Settings → Data API** → kapat (Django'nun bu API'ye ihtiyacı yok) |
| `AUTH_USER_MODEL refers to model ... that has not been installed` | `accounts` `INSTALLED_APPS`'te yok veya migration sırası bozuk | `accounts`'u ekle. Prototipte en kolayı: `db.sqlite3` ve migration dosyalarını silip yeniden oluşturmak |
| Hook çalışmıyor / `ruff` bulunamadı | Claude Code venv aktif değilken başlatıldı | Çık, `source .venv/bin/activate`, sonra `claude` |
| Stop hook Claude'u bitirtmiyor | `manage.py check` gerçekten hata veriyor | Claude'a hatayı düzelttir. Acil durumda `/hooks` ile hook'ları gör veya settings.json'dan geçici olarak kaldır |
| Vercel build'i Python sürümü hatası veriyor | Sürüm belirtilmemiş | `.python-version` (3.12) ve `pyproject.toml` içinde `requires-python = ">=3.12"` olsun |
| Oy verince sayfa yenileniyor (fetch çalışmıyor) | JS hatası veya CSRF header'ı eksik | Tarayıcı konsoluna bak. Claude'a "/ui-kontrol" çalıştırt |

---

## 10. Kaynaklar

**Claude Code**
- [Dokümantasyon](https://code.claude.com/docs/en/overview) · [Skill'ler](https://code.claude.com/docs/en/skills) · [Alt ajanlar](https://code.claude.com/docs/en/sub-agents) · [Hook'lar](https://code.claude.com/docs/en/hooks) · [MCP](https://code.claude.com/docs/en/mcp) · [İzin modları](https://code.claude.com/docs/en/permission-modes) · [Chrome ile kullanım](https://code.claude.com/docs/en/chrome)

**Django**
- [Django 6.1 dokümantasyonu](https://docs.djangoproject.com/en/6.1/) · [Özel kullanıcı modeli](https://docs.djangoproject.com/en/6.1/topics/auth/customizing/) · [İmzalı çerezler](https://docs.djangoproject.com/en/6.1/ref/request-response/#django.http.HttpResponse.set_signed_cookie) · [Kısıtlar (constraints)](https://docs.djangoproject.com/en/6.1/ref/models/constraints/)

**Vercel**
- [Django'yu Vercel'de yayınlama](https://vercel.com/docs/frameworks/full-stack/django) · [Zero-config Django duyurusu](https://vercel.com/changelog/zero-configuration-django-support) · [Vercel MCP](https://vercel.com/docs/ai-resources/vercel-mcp)

**Supabase**
- [Postgres'e bağlanma ve pooler modları](https://supabase.com/docs/guides/database/connecting-to-postgres/serverless-drivers) · [Bağlantı havuzu ve limitler](https://supabase.com/docs/guides/database/connecting-to-postgres/pooling-and-limits) · [Data API ve güvenlik](https://supabase.com/docs/guides/database/data-api) · [Supabase MCP](https://github.com/supabase-community/mcp-server-supabase)

**MCP sunucuları**
- [Context7](https://context7.com/docs/clients/claude-code) · [Playwright MCP](https://github.com/microsoft/playwright-mcp)
