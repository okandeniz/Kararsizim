# Claude Code ile Web Uygulaması Geliştirme: Araçlar ve Özellikler Rehberi

> **Kapsam:** Claude Code'un web uygulaması geliştirirken işine yarayacak yerleşik özellikleri (CLAUDE.md, skill'ler, alt ajanlar, hook'lar, komutlar, izinler) ve ona bağlayabileceğin harici araçlar (MCP sunucuları, eklentiler, tarayıcı entegrasyonu).
> **Güncellik:** Kasım 2026 itibarıyla resmi dokümantasyondan (code.claude.com/docs) derlendi. Claude Code her hafta güncellendiği için ayrıntılar değişebilir. Güncel sürüm notları için oturum içinde `/release-notes` komutunu çalıştır.
> **Kullanım önerisi:** Bu dosyayı projenin köküne `docs/claude-code-rehberi.md` olarak koyabilirsin. CLAUDE.md dosyandan `@docs/claude-code-rehberi.md` ile içe aktarma. Aktarırsan her oturumda bağlamı (context) doldurur. Gerektiğinde Claude'a "rehbere bak" demen yeterli.

---

## İçindekiler

1. [Kurulum ve ilk adımlar](#1-kurulum-ve-ilk-adımlar)
2. [Yapı taşları: hangisini ne zaman kullanmalı?](#2-yapı-taşları-hangisini-ne-zaman-kullanmalı)
3. [Proje dizin yapısı (`.claude/`)](#3-proje-dizin-yapısı-claude)
4. [CLAUDE.md ve hafıza](#4-claudemd-ve-hafıza)
5. [Yerleşik komutlar (slash commands)](#5-yerleşik-komutlar-slash-commands)
6. [Skill'ler (özel komutlar)](#6-skiller-özel-komutlar)
7. [Alt ajanlar (subagents)](#7-alt-ajanlar-subagents)
8. [Hook'lar (otomatik tetikleyiciler)](#8-hooklar-otomatik-tetikleyiciler)
9. [MCP sunucuları (harici araç bağlantıları)](#9-mcp-sunucuları-harici-araç-bağlantıları)
10. [Eklentiler (plugins) ve marketplace'ler](#10-eklentiler-plugins-ve-marketplaceler)
11. [Tarayıcıda test ve doğrulama](#11-tarayıcıda-test-ve-doğrulama)
12. [İzinler, güvenlik ve settings.json](#12-izinler-güvenlik-ve-settingsjson)
13. [Paralel çalışma](#13-paralel-çalışma)
14. [Kod inceleme ve kalite](#14-kod-inceleme-ve-kalite)
15. [Otomasyon ve programatik kullanım](#15-otomasyon-ve-programatik-kullanım)
16. [Model, bağlam ve maliyet yönetimi](#16-model-bağlam-ve-maliyet-yönetimi)
17. [Önerilen web uygulaması iş akışı](#17-önerilen-web-uygulaması-iş-akışı)
18. [Hızlı başvuru: CLI komutları](#18-hızlı-başvuru-cli-komutları)
19. [Kaynaklar](#19-kaynaklar)

---

## 1. Kurulum ve ilk adımlar

### Gereksinimler
- macOS 13+, Windows 10 1809+, Ubuntu 20.04+, Debian 10+ veya Alpine 3.19+
- 4 GB+ RAM, internet bağlantısı
- **Pro, Max, Team, Enterprise veya Console hesabı.** Ücretsiz claude.ai planı Claude Code içermez.

### Kurulum

```bash
# macOS / Linux / WSL (önerilen, otomatik güncellenir)
curl -fsSL https://claude.ai/install.sh | bash

# Windows PowerShell
irm https://claude.ai/install.ps1 | iex

# Homebrew (otomatik güncellenmez)
brew install --cask claude-code

# WinGet
winget install Anthropic.ClaudeCode

# npm (Node.js 22+; sudo kullanma)
npm install -g @anthropic-ai/claude-code
```

### Doğrulama ve başlatma

```bash
claude --version     # sürümü gösterir
claude doctor        # kurulum ve ayar teşhisi (oturum açmadan)
cd web-uygulamam
claude               # etkileşimli oturum başlatır, ilk seferde tarayıcıdan giriş ister
claude update        # elle güncelleme
```

### Arayüz seçenekleri
| Arayüz | Not |
|---|---|
| Terminal (CLI) | Ana deneyim. Tüm özellikler burada. |
| VS Code eklentisi | Satır içi diff, @-mention, plan inceleme |
| JetBrains IDE'leri | IntelliJ, WebStorm vb. |
| Desktop uygulaması | Paralel oturumlar, görsel diff, **yerleşik tarayıcı**, bilgisayar kullanımı |
| Web / mobil | Bulut oturumları, GitHub reposu üzerinde çalışır |

---

## 2. Yapı taşları: hangisini ne zaman kullanmalı?

| Özellik | Ne işe yarar | Ne zaman kullan | Konum |
|---|---|---|---|
| **CLAUDE.md** | Her oturumda yüklenen kalıcı talimatlar | Proje mimarisi, komutlar, kod standartları | `./CLAUDE.md` |
| **Skill** | İhtiyaç anında yüklenen talimat paketi / `/komut` | Tekrarlanan iş akışları (yeni bileşen, deploy, migration) | `.claude/skills/<ad>/SKILL.md` |
| **Alt ajan (subagent)** | Kendi bağlamı ve araç seti olan uzman yardımcı | Kod inceleme, test yazma, araştırma (ana bağlamı kirletmeden) | `.claude/agents/<ad>.md` |
| **Hook** | Belirli olaylarda **kesin** çalışan komut | Format/lint, dosya koruma, test zorunluluğu | `.claude/settings.json` |
| **MCP sunucusu** | Harici sistemlere bağlantı (DB, deploy, tasarım, tarayıcı) | Supabase, Vercel, Figma, Playwright vb. | `.mcp.json` |
| **Eklenti (plugin)** | Yukarıdakilerin paketlenmiş hali | Hazır çözüm kurmak veya ekiple paylaşmak | `/plugin install` |

> **Önemli fark:** CLAUDE.md ve skill'ler *tavsiyedir*: Claude bunları bağlam olarak okur ama bir eylemi garanti altına almaz. Bir şeyin **kesinlikle** olmasını ya da engellenmesini istiyorsan hook veya izin kuralı (`permissions.deny`) kullan.

---

## 3. Proje dizin yapısı (`.claude/`)

```text
web-uygulamam/
├── CLAUDE.md                 # Ekip talimatları (git'e commit et)
├── CLAUDE.local.md           # Kişisel notlar (.gitignore'a ekle)
├── .mcp.json                 # Proje MCP sunucuları (git'e commit et)
└── .claude/
    ├── settings.json         # Ekip ayarları: izinler, hook'lar, env (commit et)
    ├── settings.local.json   # Kişisel ayarlar (commit etme)
    ├── rules/                # Konuya / dosya yoluna göre kurallar
    │   ├── frontend.md
    │   └── api.md
    ├── skills/
    │   └── new-component/
    │       └── SKILL.md
    ├── agents/
    │   └── code-reviewer.md
    └── hooks/
        └── format-and-lint.sh

~/.claude/                    # Kullanıcı düzeyi (tüm projelerin)
├── CLAUDE.md
├── settings.json
├── rules/
├── skills/
└── agents/
~/.claude.json                # local/user kapsamlı MCP sunucuları, durum
```

---

## 4. CLAUDE.md ve hafıza

### Yükleme yerleri

| Tür | Konum | Paylaşım |
|---|---|---|
| Kurumsal (managed) | `/etc/claude-code/CLAUDE.md` (Linux), `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | Tüm organizasyon |
| Kullanıcı | `~/.claude/CLAUDE.md` | Sadece sen, tüm projeler |
| Proje | `./CLAUDE.md` veya `./.claude/CLAUDE.md` | Ekip (git) |
| Yerel | `./CLAUDE.local.md` | Sadece sen, bu proje |

- Çalışma dizini ve üstündeki tüm CLAUDE.md'ler oturum başında birleştirilerek yüklenir. Alt dizinlerdekiler, Claude o dizindeki bir dosyaya dokunduğunda yüklenir. Bu, monorepo'da `apps/web/CLAUDE.md` ile `apps/api/CLAUDE.md` ayrımı için idealdir.
- **AGENTS.md desteği:** CLAUDE.md yoksa Claude, repodaki `AGENTS.md` dosyasını okur. İkisi birden varsa CLAUDE.md kazanır. Ortak kullanım için CLAUDE.md içine `@AGENTS.md` yaz.
- **Boyut:** Dosya başına **200 satırın altında** tut. Uzun dosyalar bağlamı doldurur ve talimatlara uyumu düşürür.
- **`/init`** kod tabanını analiz edip başlangıç CLAUDE.md'si oluşturur. Dosya varsa iyileştirme önerir.
- **`/memory`** CLAUDE.md dosyalarını düzenlemeni ve otomatik hafızayı açıp kapatmanı sağlar.

### İçe aktarma (`@import`)

```markdown
Proje genel bakışı için @README.md dosyasına bak.
API sözleşmeleri: @docs/api-contracts.md
```

### Dosya yoluna göre kurallar (`.claude/rules/`)

Bu kurallar yalnızca eşleşen dosyalarla çalışılırken bağlama girer:

```markdown
---
paths:
  - "src/components/**/*.tsx"
  - "src/app/**/*.tsx"
---

# Frontend kuralları
- Sunucu bileşenlerini varsayılan yap; "use client" yalnızca etkileşim gerekiyorsa.
- Stil için Tailwind kullan; inline style yazma.
- Her yeni bileşene bir Storybook hikayesi veya test ekle.
```

### Otomatik hafıza (auto memory)
Claude, düzeltmelerinden ve tercihlerinden öğrendiklerini kendi tutar (`~/.claude/projects/<proje>/memory/`). Her oturumda ilk 200 satır veya 25 KB yüklenir. `/memory` ile görüntüleyip açıp kapatabilirsin.

### Web uygulaması için örnek CLAUDE.md

```markdown
# Proje: Acme Web

## Teknoloji yığını
- Next.js 16 (App Router), TypeScript (strict), Tailwind CSS, shadcn/ui
- Veritabanı: Supabase (Postgres + Auth + Storage), Drizzle ORM
- Test: Vitest (birim), Playwright (uçtan uca)
- Deploy: Vercel

## Komutlar
- Geliştirme sunucusu: `pnpm dev` (http://localhost:3000)
- Tip kontrolü: `pnpm typecheck`
- Lint: `pnpm lint`
- Birim test: `pnpm test`
- E2E test: `pnpm test:e2e`
- DB migration: `pnpm db:migrate`

## Mimari
- `src/app/`: route'lar ve sayfalar
- `src/components/ui/`: shadcn bileşenleri (elle düzenleme; CLI ile güncelle)
- `src/lib/`: yardımcılar, DB istemcisi
- `src/server/`: server action'lar ve iş mantığı

## Kurallar
- Bir değişikliği bitmiş saymadan önce `pnpm typecheck && pnpm test` çalıştır.
- `.env*` dosyalarını asla okuma veya değiştirme.
- Yeni bağımlılık eklemeden önce sor.
- Commit mesajları Conventional Commits formatında olsun.
```

---

## 5. Yerleşik komutlar (slash commands)

Oturumda `/` yazınca tüm komutlar listelenir. Web geliştirmede en çok işine yarayanlar:

### Proje kurulumu ve yapılandırma
| Komut | Açıklama |
|---|---|
| `/init` | Kod tabanından CLAUDE.md oluşturur |
| `/memory` | CLAUDE.md ve otomatik hafızayı yönetir |
| `/config [key=value]` | Ayarlar arayüzü. Değeri doğrudan da atayabilirsin |
| `/permissions` | allow / ask / deny kurallarını yönetir |
| `/mcp` | MCP sunucularının durumu, OAuth girişi, yeniden bağlanma |
| `/plugin` | Eklenti menüsü (Discover, Installed, Marketplaces, Errors) |
| `/hooks` | Hook yapılandırmalarını gösterir |
| `/agents` | Alt ajan yönetimi hatırlatması |
| `/skills` | Mevcut skill'leri listeler ve token maliyetine göre sıralar |
| `/update-config` | "Şu komuta izin ver / şu hook'u ekle" gibi isteklerle settings.json'u Claude'a düzenletir |
| `/fewer-permission-prompts` | Geçmiş oturumları tarayıp güvenli komutlar için allowlist önerir |
| `/import [codex\|gemini\|cursor]` | Diğer araçlardaki yapılandırmayı (talimatlar, MCP vb.) taşır |
| `/doctor` | Kurulum, ayar ve CLAUDE.md sorunlarını teşhis edip düzeltir |
| `/ide` | IDE entegrasyonu durumu |
| `/terminal-setup` | Shift+Enter ile yeni satır kısayolunu kurar |
| `/statusline` | Durum çubuğunu özelleştirir |

### Planlama ve geliştirme
| Komut | Açıklama |
|---|---|
| `/plan [açıklama]` | Plan moduna girer: önce araştırır, sen onaylamadan dosya düzenlemez |
| `/design [brief]` | UI mockup'ları, ekran akışları, landing page taslakları (artboard). Seçtiğini uygular |
| `/design-sync` | Repodaki React tasarım sistemini Claude Design'a yükler; tasarımlar gerçek bileşenlerini kullanır |
| `/run` | Uygulamayı başlatıp çalıştırarak değişikliği **canlı** görür |
| `/verify` | Değişikliğin gerçekten çalıştığını uygulamayı derleyip çalıştırarak doğrular |
| `/run-skill-generator` | `/run` ve `/verify`'a projeni nasıl derleyip başlatacağını öğreten skill yazar |
| `/goal [koşul]` | Koşul sağlanana kadar Claude'un turlar boyunca çalışmasını sürdürür (ör. "tüm testler geçene kadar") |
| `/batch <talimat>` | Büyük çaplı değişikliği 5–30 bağımsız parçaya böler ve paralel alt ajanlarla uygular |
| `/btw [soru]` | Konuşmaya eklenmeyen yan soru sorar |
| `/diff` | Çalışma ağacındaki değişiklikleri inceler |
| `/rewind` | Konuşmayı ve/veya kodu önceki bir noktaya geri alır (takma adları: `/undo`, `/checkpoint`) |

### Kalite ve güvenlik
| Komut | Açıklama |
|---|---|
| `/code-review [seviye] [--fix] [pr#\|branch]` | Diff'i doğruluk hataları için inceler. Takma adı: `/review` |
| `/code-review ultra` / `/ultrareview` | Bulutta çok ajanlı derin inceleme |
| `/security-review` | Branch değişikliklerini enjeksiyon, auth, veri sızıntısı gibi açıklar için tarar |
| `/simplify` | Değişen kodu dört paralel ajanla sadeleştirir |
| `/install-github-app` | Claude GitHub App'i ve GitHub Actions iş akışlarını kurar |
| `/autofix-pr` | PR'ı izleyen ve CI hatalarını / yorumları düzelten bulut oturumu başlatır |

### Oturum ve bağlam
| Komut | Açıklama |
|---|---|
| `/clear` | Yeni, boş bir konuşma başlatır |
| `/compact [odak]` | Konuşmayı özetleyerek bağlamda yer açar |
| `/context` | Bağlam kullanımını renkli ızgara olarak gösterir |
| `/resume` | Eski bir oturuma döner |
| `/branch` | Konuşmayı dallandırır (farklı bir yön denemek için) |
| `/fork [prompt]` | Konuşmanın kopyasını arka planda çalıştırır, sen burada devam edersin |
| `/subtask <görev>` | Tüm konuşmayı miras alan arka plan alt ajanı başlatır |
| `/tasks` | Arka plan işlerini (alt ajanlar, shell'ler) yönetir |
| `/cd <yol>` | Oturumu başka bir dizine taşır |
| `/add-dir <yol>` | Oturuma ek çalışma dizini ekler (ör. ayrı backend reposu) |

### Model ve kullanım
| Komut | Açıklama |
|---|---|
| `/model` | Model seçimi |
| `/effort [low…xhigh\|max\|auto]` | Düşünme derinliği |
| `/fast` | Hızlı modu açar/kapatır |
| `/usage` | Maliyet, plan limitleri, neyin limit tükettiği (`/cost`, `/stats` takma adları) |
| `/output-style` | Yanıt stili (ör. `concise`) |

### Otomasyon
| Komut | Açıklama |
|---|---|
| `/loop [aralık] [prompt]` | Oturum açıkken bir komutu tekrar tekrar çalıştırır (ör. CI'ı izle) |
| `/schedule` | Bulutta zamanlanmış görev oluşturur |
| `/background` | Oturumu arka plan ajanına çevirir, terminali serbest bırakır |
| `/chrome` | Claude in Chrome bağlantısını yönetir |

**Kısayollar:** `Shift+Tab` izin modları arasında geçiş yapar. `Esc` Claude'u durdurur. `Esc Esc` geri sarma menüsünü açar. `Ctrl+B` çalışan işi arka plana alır. `Ctrl+O` ayrıntıları genişletir. `!komut` doğrudan shell komutu çalıştırır. `@dosya` dosyayı bağlama ekler.

---

## 6. Skill'ler (özel komutlar)

Skill, YAML frontmatter ve Markdown talimatlarından oluşan bir `SKILL.md` dosyasıdır. Claude ilgili gördüğünde otomatik yükler, sen de `/skill-adı` ile doğrudan çağırabilirsin. Gövde yalnızca kullanıldığında yüklenir, bu yüzden uzun referans materyali ucuzdur.

> Eski `.claude/commands/deploy.md` biçimi hâlâ çalışır, ama artık skill'lerle birleştirildi. Önerilen biçim `.claude/skills/deploy/SKILL.md`.

### Konumlar
| Kapsam | Yol |
|---|---|
| Kişisel | `~/.claude/skills/<ad>/SKILL.md` |
| Proje | `.claude/skills/<ad>/SKILL.md` |
| Alt dizin | `<dizin>/.claude/skills/<ad>/SKILL.md` |
| Eklenti | `<eklenti>/skills/<ad>/SKILL.md` → `/eklenti-adı:skill-adı` |

### Frontmatter alanları (hepsi isteğe bağlı)
| Alan | Amaç |
|---|---|
| `name` | `/` menüsündeki ad (varsayılan: dizin adı) |
| `description` | **Ne yaptığı ve ne zaman kullanılacağı.** Otomatik tetikleme buna bağlıdır |
| `when_to_use` | Ek tetikleyici ifadeler |
| `argument-hint` | Otomatik tamamlama ipucu, ör. `[bileşen-adı]` |
| `disable-model-invocation: true` | Yalnızca sen çağırabilirsin (deploy gibi riskli işler için) |
| `user-invocable: false` | `/` menüsünde görünmez, yalnızca Claude çağırır |
| `allowed-tools` | Skill çalıştığı turda izin istemeden kullanılabilecek araçlar |
| `disallowed-tools` | Skill aktifken kaldırılan araçlar |
| `model`, `effort` | Bu tur için model / efor ayarı |
| `context: fork` + `agent` | Skill'i ayrı bir alt ajanda çalıştırır (ör. `agent: Explore`) |
| `paths` | Otomatik yüklemeyi eşleşen dosyalarla sınırlar |
| `hooks` | Skill çağrıldığında kaydedilen hook'lar |

### Argümanlar ve dinamik bağlam
- `$ARGUMENTS`: tüm argümanlar. `$0`, `$1`, `$2`: konumsal argümanlar.
- `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`: yol değişkenleri.
- `` !`komut` ``: Claude skill'i görmeden önce shell komutunu çalıştırır ve çıktıyı yerine koyar.

### Örnek 1: Yeni bileşen oluşturma

`.claude/skills/new-component/SKILL.md`

```markdown
---
description: Yeni bir React bileşeni oluşturur (TS + Tailwind + test). Kullanıcı yeni bileşen, UI parçası veya sayfa bölümü istediğinde kullan.
argument-hint: "[BileşenAdı] [klasör]"
allowed-tools: Bash(pnpm test *) Bash(pnpm typecheck)
---

`$0` adında bir bileşeni `src/components/$1/` altında oluştur:

1. `$0.tsx`: tipli props, Tailwind ile stil, gerekiyorsa shadcn/ui bileşenleri.
2. `$0.test.tsx`: Vitest + Testing Library ile render ve etkileşim testi.
3. `index.ts`: dışa aktarım.
4. `pnpm typecheck` ve `pnpm test -- $0` çalıştır; hata varsa düzelt.

Mevcut bileşen örnekleri için @src/components/ui/button.tsx dosyasına bak.
```

Kullanım: `/new-component PricingCard marketing`

### Örnek 2: Elle tetiklenen deploy

`.claude/skills/deploy/SKILL.md`

```markdown
---
name: deploy
description: Uygulamayı production'a deploy eder
disable-model-invocation: true
allowed-tools: Bash(pnpm *) Bash(git status *) Bash(vercel *)
---

## Mevcut durum
- Branch: !`git branch --show-current`
- Commit edilmemiş değişiklikler: !`git status --short`

## Adımlar
1. Commit edilmemiş değişiklik varsa dur ve bildir.
2. `pnpm typecheck && pnpm lint && pnpm test` çalıştır.
3. `pnpm build` ile derle.
4. `vercel --prod` ile deploy et ve URL'yi raporla.
```

### Örnek 3: PR özetini alt ajanda çıkarma

```markdown
---
name: pr-summary
description: Bir pull request'teki değişiklikleri özetler
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

- PR diff: !`gh pr diff`
- Değişen dosyalar: !`gh pr diff --name-only`

Bu PR'ı özetle; riskli değişiklikleri ve eksik testleri listele.
```

### Yerleşik (bundled) skill'ler
`/code-review`, `/batch`, `/debug`, `/loop`, `/claude-api`, `/verify`, `/run`, `/simplify`, `/design`, `/doctor` ve diğerleri. Aynı adlı bir skill yazarsan yerleşik olanın yerine seninki geçer.

> **İpucu:** `SKILL.md` dosyasını 500 satırın altında tut. Ayrıntıları aynı klasördeki `reference.md`, `examples.md` veya `scripts/` dosyalarına koyup SKILL.md'den bunlara referans ver. Skill dosyalarındaki değişiklikler oturumu yeniden başlatmadan etkinleşir.

---

## 7. Alt ajanlar (subagents)

Alt ajan, kendi sistem prompt'u, araç seti ve bağlam penceresi olan uzman bir yardımcıdır. Ana konuşmanın bağlamını kirletmeden iş yapar ve sonucu geri raporlar.

### Yerleşik alt ajanlar
| Ad | Görev |
|---|---|
| **Explore** | Hızlı, salt okunur kod tabanı araması |
| **Plan** | Plan modunda kullanılan salt okunur araştırma ajanı |
| **general-purpose** | Keşif ve değişiklik içeren çok adımlı görevler |
| **claude-code-guide** | Claude Code özellikleri hakkındaki soruları yanıtlar |

### Konumlar (öncelik sırasıyla)
1. Kurumsal managed ayarlar
2. `--agents` CLI bayrağı (yalnızca o oturum)
3. `.claude/agents/` (proje)
4. `~/.claude/agents/` (kullanıcı)
5. Eklentinin `agents/` dizini

### Frontmatter alanları
Yalnızca `name` ve `description` zorunludur.

| Alan | Değerler / amaç |
|---|---|
| `tools` | İzin verilen araçlar listesi (boşsa hepsini miras alır) |
| `disallowedTools` | Yasaklı araçlar |
| `model` | `sonnet`, `opus`, `haiku`, `fable`, tam model ID veya `inherit` |
| `permissionMode` | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | Tur sınırı |
| `skills` | Başlangıçta önceden yüklenen skill'ler |
| `mcpServers` | Bu ajana özel MCP sunucuları |
| `hooks` | Bu ajana özel hook'lar |
| `memory` | Kalıcı hafıza: `user`, `project`, `local` |
| `background` | `true` ise hep arka planda çalışır |
| `isolation: worktree` | Geçici bir git worktree'de çalışır (çakışmasız) |
| `effort` | `low` … `max` |
| `color` | Arayüz rengi |

### Örnek: Kod inceleyici

`.claude/agents/code-reviewer.md`

```markdown
---
name: code-reviewer
description: Kodu kalite, güvenlik ve en iyi uygulamalar açısından inceler. Kod değişikliklerinden sonra proaktif olarak kullan.
tools: Read, Grep, Glob, Bash
model: sonnet
memory: project
color: blue
---

Kıdemli bir web geliştirici olarak değişen kodu incele:
- Güvenlik: XSS, SQL enjeksiyonu, auth kontrolleri, sızan secret'lar
- Next.js: server/client sınırı, gereksiz "use client", veri çekme desenleri
- Erişilebilirlik: semantik HTML, aria etiketleri, klavye erişimi
- Performans: gereksiz render, büyük bundle'lar, optimize edilmemiş görseller

Her bulgu için dosya:satır, sorun ve somut düzeltme öner.
Tekrarlayan sorunları ve proje konvansiyonlarını ajan hafızana kaydet.
```

### Örnek: Test yazarı

`.claude/agents/test-writer.md`

```markdown
---
name: test-writer
description: Yeni veya değişen kod için Vitest birim testleri ve Playwright e2e testleri yazar. Özellik tamamlandığında kullan.
tools: Read, Write, Edit, Grep, Glob, Bash
isolation: worktree
---

Değişen dosyaları bul, mevcut test desenlerini takip ederek eksik testleri yaz,
`pnpm test` ile çalıştır ve tüm testler geçene kadar düzelt.
Uygulama kodunu değiştirme; yalnızca test dosyalarına dokun.
```

### Kullanım
```text
code-reviewer alt ajanını kullanarak son değişikliklerimi incele
@"code-reviewer (agent)" auth akışına bak
```

### Davranış notları
- Claude'un başlattığı alt ajanlar varsayılan olarak **arka planda** çalışır. Sonuç, bir sonraki turda bildirim olarak gelir.
- Alt ajanlar kendi alt ajanlarını başlatabilir (varsayılan 3 seviye derinlik) ve aynı anda 20'ye kadar alt ajan çalışabilir.
- Oturumluk ajan tanımlamak için:
  ```bash
  claude --agents '{"reviewer":{"description":"Kod inceleyici","prompt":"Sen kıdemli bir inceleyicisin.","tools":["Read","Grep"],"model":"sonnet"}}'
  ```

---

## 8. Hook'lar (otomatik tetikleyiciler)

Hook'lar Claude Code'un yaşam döngüsündeki belirli noktalarda **her seferinde, kesin olarak** çalışan işleyicilerdir. Bir işleyici shell komutu, HTTP isteği, MCP aracı, LLM prompt'u veya alt ajan olabilir.

### En önemli olaylar
| Olay | Ne zaman | Engelleyebilir mi? |
|---|---|---|
| `SessionStart` | Oturum başladığında / devam ettiğinde | Hayır (bağlam ekleyebilir) |
| `UserPromptSubmit` | Prompt gönderildiğinde, işlenmeden önce | Evet |
| `PreToolUse` | Araç çalışmadan önce | Evet |
| `PermissionRequest` | Araç izin gerektirdiğinde | JSON ile |
| `PostToolUse` | Araç başarıyla çalıştıktan sonra | Hayır (stderr Claude'a gösterilir) |
| `Stop` | Claude yanıtı bitirdiğinde | Evet (devam etmeye zorlar) |
| `SubagentStop` | Alt ajan bittiğinde | Evet |
| `PreCompact` / `PostCompact` | Bağlam sıkıştırma öncesi / sonrası | PreCompact: evet |
| `Notification` | Claude bildirim gönderdiğinde | Hayır |
| `SessionEnd` | Oturum bittiğinde | Hayır |

Diğer olaylar: `PostToolUseFailure`, `PostToolBatch`, `SubagentStart`, `TaskCreated`, `TaskCompleted`, `ConfigChange`, `CwdChanged`, `FileChanged`, `InstructionsLoaded`, `WorktreeCreate`, `WorktreeRemove`, `Elicitation`.

### Çıkış kodları
- **0:** Başarılı. Tek bir JSON nesnesi basılırsa stdout JSON olarak işlenir.
- **2:** Engelleyici hata. Engellenebilir olaylarda eylem durur ve stderr Claude'a gerekçe olarak gider.
- **Diğer (1 dahil):** Engellemeyen hata, eylem devam eder. Kural uygulamak için **`exit 2`** kullan.

### Yapı: olay → matcher → işleyici

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(rm *)",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

- `matcher`: `"Edit|Write"` (liste), `"*"` (hepsi) veya regex (`"mcp__supabase__.*"`).
- `if`: izin kuralı sözdizimiyle ek filtre, ör. `"Edit(*.ts)"`.
- Hook'a gelen JSON girdisinde `session_id`, `cwd`, `tool_name`, `tool_input` vb. bulunur.
- Ortam değişkenleri: `$CLAUDE_PROJECT_DIR`, `$CLAUDE_PLUGIN_ROOT`, `$CLAUDE_EFFORT`.

### Örnek 1: Her düzenlemeden sonra Prettier + ESLint

`.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/format-and-lint.sh",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

`.claude/hooks/format-and-lint.sh` (`chmod +x` ile çalıştırılabilir yap, `jq` gerekir)

```bash
#!/bin/bash
FILE=$(jq -r '.tool_input.file_path // empty')

case "$FILE" in
  *.ts|*.tsx|*.js|*.jsx|*.css|*.json)
    npx prettier --write "$FILE" >/dev/null 2>&1
    ;;
esac

case "$FILE" in
  *.ts|*.tsx|*.js|*.jsx)
    if ! OUT=$(npx eslint "$FILE" 2>&1); then
      echo "ESLint sorunları ($FILE):" >&2
      echo "$OUT" >&2
      exit 2   # Düzenleme geri alınmaz ama Claude hatayı görür ve düzeltir
    fi
    ;;
esac
exit 0
```

### Örnek 2: Claude bitirmeden önce tip kontrolünü zorunlu kılma

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "cd \"$CLAUDE_PROJECT_DIR\" && pnpm -s typecheck >/dev/null 2>&1 || { echo 'Tip hataları var; düzeltmeden bitirme. pnpm typecheck çalıştır.' >&2; exit 2; }",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

### Örnek 3: Tehlikeli komutları reddetme (JSON çıktısıyla)

```bash
#!/bin/bash
# .claude/hooks/guard-db.sh: PreToolUse, matcher "Bash"
CMD=$(jq -r '.tool_input.command')
if echo "$CMD" | grep -qiE 'drop (table|database)|supabase db reset'; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Yıkıcı veritabanı komutları yasak."}}
EOF
fi
exit 0
```

> **İpucu:** Hook'u elle yazmak yerine `/update-config her düzenlemeden sonra prettier çalıştıran bir hook ekle` diyebilirsin.

---

## 9. MCP sunucuları (harici araç bağlantıları)

MCP (Model Context Protocol), Claude Code'u veritabanlarına, deploy platformlarına, tasarım araçlarına, tarayıcılara ve dokümantasyon kaynaklarına bağlar.

### Temel komutlar

```bash
# Uzak HTTP sunucusu (önerilen)
claude mcp add --transport http <ad> <url>

# Header ile (token)
claude mcp add --transport http <ad> <url> --header "Authorization: Bearer TOKEN"

# Yerel stdio sunucusu ("--" sonrası doğrudan sunucuya gider)
claude mcp add --env API_KEY=xxx --transport stdio <ad> -- npx -y <paket>

# JSON ile ekleme
claude mcp add-json <ad> '{"command":"npx","args":["-y","paket"]}'

claude mcp list            # sunucular ve sağlık durumu
claude mcp get <ad>        # ayrıntılar
claude mcp remove <ad>     # kaldır (OAuth token'ları da silinir)
claude mcp login <ad>      # shell'den OAuth girişi
claude mcp logout <ad>     # kimlik bilgilerini temizle
```

Oturum içinde `/mcp` komutuyla durumu görebilir, kimlik doğrulayabilir, yeniden bağlanabilir ve sunucuları açıp kapatabilirsin.

### Kapsamlar (`--scope`)
| Kapsam | Nerede yüklenir | Paylaşım | Saklandığı yer |
|---|---|---|---|
| `local` (varsayılan) | Yalnızca bu proje | Hayır | `~/.claude.json` |
| `project` | Bu proje | **Evet, git ile** | `.mcp.json` (proje kökü) |
| `user` | Tüm projelerin | Hayır | `~/.claude.json` |

### Ekip için `.mcp.json` (ortam değişkeni genişletmeli)

```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=${SUPABASE_PROJECT_REF}&read_only=true"
    },
    "vercel": {
      "type": "http",
      "url": "https://mcp.vercel.com"
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp",
      "headers": { "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}" }
    }
  }
}
```

`${VAR}` ve `${VAR:-varsayilan}` sözdizimi `command`, `args`, `env`, `url` ve `headers` alanlarında çalışır. Secret'ları dosyaya yazma, ortam değişkeninden oku. Proje kapsamlı sunucular ilk kullanımda onay ister.

### Web geliştirme için önerilen MCP sunucuları

| Kategori | Sunucu | Kurulum komutu | Ne sağlar |
|---|---|---|---|
| **Tarayıcı testi** | Playwright (Microsoft) | `claude mcp add playwright -- npx @playwright/mcp@latest` | Gerçek tarayıcıda gezinme, tıklama, form doldurma, ekran görüntüsü (erişilebilirlik ağacıyla). `--headless`, `--browser firefox` gibi bayraklar en sona eklenir |
| **Güncel dokümantasyon** | Context7 | `claude mcp add --transport http context7 https://mcp.context7.com/mcp --header "CONTEXT7_API_KEY: KEY"` veya `npx ctx7 setup --claude` | Kütüphanelerin güncel dokümanları ve kod örnekleri (eğitim verisindeki eski API'ler yerine) |
| **Backend / DB** | Supabase | `claude mcp add --transport http supabase https://mcp.supabase.com/mcp` | Tablo sorgulama, şema inceleme, migration, loglar, TypeScript tip üretimi. OAuth. `?read_only=true` ve `?project_ref=` parametreleri |
| **Deploy** | Vercel | `claude mcp add --transport http vercel https://mcp.vercel.com` | Projeler, deployment'lar, build/runtime logları, dokümantasyon araması. OAuth |
| **Next.js** | Next.js DevTools (Vercel) | `claude mcp add next-devtools npx next-devtools-mcp@latest` | Çalışan Next.js dev sunucusuna bağlanır: route yapısı, hatalar, dokümanlar (Next.js 16+) |
| **Tasarım** | Figma | `claude mcp add --transport http figma https://mcp.figma.com/mcp` | Bileşenler, değişkenler, layout verisi ile tasarımdan koda. `/mcp` → figma → Authenticate |
| **UI bileşenleri** | shadcn/ui | `pnpm dlx shadcn@latest mcp init --client claude` | shadcn registry'sinden bileşen arama ve kurma |
| **Hata izleme** | Sentry | `claude mcp add --transport http sentry https://mcp.sentry.dev/mcp` | Hata, trace ve log arama. OAuth |
| **Kod barındırma** | GitHub | `claude mcp add --transport http github https://api.githubcopilot.com/mcp/ --header "Authorization: Bearer GITHUB_PAT"` | Issue, PR, kod inceleme. (Alternatif: `gh` CLI zaten kuruluysa Claude onu doğrudan kullanabilir) |
| **Ödeme** | Stripe | `claude mcp add --transport http stripe https://mcp.stripe.com` | Stripe hesabı üzerinde işlemler |
| **PostgreSQL** | DBHub | `claude mcp add --transport stdio db -- npx -y @bytebase/dbhub --dsn "postgresql://readonly:pass@host:5432/db"` | Herhangi bir Postgres'e (**salt okunur kullanıcıyla**) bağlanma |

Diğer resmi örnekler: Notion, Asana, Airtable, HubSpot, Slack, Jira, Linear. Daha fazlası için [Anthropic Directory](https://claude.ai/directory).

### Limitler ve ayarlar
- MCP araç çıktısı 10.000 token'ı geçince uyarı verilir. Varsayılan üst sınır 25.000 token'dır: `MAX_MCP_OUTPUT_TOKENS=50000 claude`
- Zaman aşımları: `MCP_TIMEOUT` (başlangıç), `MCP_TOOL_TIMEOUT` (araç çağrısı, ms)
- **Tool search** varsayılan olarak açıktır: araç tanımları baştan yüklenmez, ihtiyaç anında bulunur. Böylece çok sunucu eklemek bağlamı şişirmez.

> **Güvenlik:** Production veritabanına bağlanırken salt okunur kullanıcı veya `read_only=true` kullan. Üçüncü taraf MCP sunucularını kurmadan önce kaynağını incele.

---

## 10. Eklentiler (plugins) ve marketplace'ler

Eklenti; skill, alt ajan, hook, MCP sunucusu ve LSP (dil sunucusu) bileşenlerini tek pakette toplar. Hazır bir kurulum almanın veya kendi kurulumunu ekiple paylaşmanın en kolay yoludur.

### Anthropic marketplace'leri
| Marketplace | Ad (`@` sonrası) | Nasıl eklenir |
|---|---|---|
| Resmi | `claude-plugins-official` | İlk etkileşimli oturumda otomatik eklenir |
| Topluluk | `claude-community` | `/plugin marketplace add anthropics/claude-plugins-community` |
| Demo | `claude-code-plugins` | `/plugin marketplace add anthropics/claude-code` |

Web'de göz atmak için: [claude.com/marketplace/plugins](https://claude.com/marketplace/plugins). Oturum içinde: `/plugin` → **Discover** sekmesi.

### Temel komutlar

```text
/plugin                                   # menü
/plugin install <ad>@<marketplace>        # kurulum
/plugin list                              # kurulu eklentiler
/plugin enable | disable <ad>
/plugin marketplace add <owner>/<repo>    # üçüncü taraf marketplace ekle
/reload-plugins                           # yeniden başlatmadan uygula
```

### Web geliştiricisi için faydalı eklentiler

| Eklenti | Kaynak | Açıklama |
|---|---|---|
| `typescript-lsp` | resmi | **Kesinlikle kur.** Claude her düzenlemeden sonra tip hatalarını görür ve sembolle gezinir. Önce: `npm install -g typescript-language-server typescript` |
| `commit-commands` | resmi | Commit / push / PR iş akışı komutları |
| `code-review` | resmi | PR inceleme iş akışı |
| `feature-dev` | resmi | Özellik geliştirme iş akışı |
| `security-guidance` | resmi | Claude yazarken değişiklikleri güvenlik açıkları için inceler |
| Claude Security | resmi | Kod tabanında çok ajanlı güvenlik taraması; seçtiğin bulguları yamaya çevirir |
| Figma eklentisi | Figma | Figma MCP + tasarımdan koda skill'leri (Figma'nın önerdiği kurulum yolu) |
| Context7 eklentisi | Context7 | MCP + kullanım skill'i |
| `sentry-mcp` | `getsentry/sentry-mcp` | Sentry sorularını otomatik devralan alt ajan |

```text
/plugin install typescript-lsp@claude-plugins-official
/plugin install security-guidance@claude-plugins-official
```

Diğer diller için LSP eklentileri: `pyright-lsp` (Python), `gopls-lsp` (Go), `rust-analyzer-lsp`, `php-lsp`, `ruby-lsp`, `jdtls-lsp` (Java), `csharp-lsp`.

> **Güvenlik:** Anthropic üçüncü taraf marketplace'leri incelemez. Eklentiler makinende kod çalıştırabilir, bu yüzden kurmadan önce içeriğine bak.

### Kendi eklentini oluşturma (özet)
```text
my-plugin/
├── .claude-plugin/plugin.json   # manifest
├── skills/
├── agents/
├── hooks/
└── .mcp.json
```
Yerelde denemek için: `claude --plugin-dir ./my-plugin`. Ayrıntılar: [Create a plugin](https://code.claude.com/docs/en/plugins/create).

---

## 11. Tarayıcıda test ve doğrulama

Web uygulamasında "testler geçti" demek yetmez, arayüzün gerçekten çalıştığını görmek gerekir. Seçeneklerin:

### A) Claude in Chrome (gerçek tarayıcın, oturumlarınla)
```bash
claude --chrome        # veya oturumda /chrome → "Enabled by default"
```
- **Gereksinimler:** Chrome, Edge veya başka bir Chromium tarayıcı + [Claude in Chrome eklentisi](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) + doğrudan Anthropic planı (Pro/Max/Team/Enterprise) ve `/login` ile giriş. WSL'de desteklenmez.
- **Yapabildikleri:** `localhost`'u açar; formu test eder; **konsol hatalarını ve DOM'u okur** ve hataya yol açan kodu düzeltir; Figma tasarımıyla karşılaştırır; GIF kaydeder; ekran görüntüsü kaydeder.
- **Örnek prompt:**
  ```text
  localhost:3000/login'i aç, formu geçersiz verilerle gönder ve
  hata mesajlarının doğru göründüğünü kontrol et. Konsolda hata varsa düzelt.
  ```
- Giriş sayfası veya CAPTCHA çıkınca Claude durur ve senden işlemi yapmanı ister.

### B) Playwright MCP (izole, tekrarlanabilir)
Bölüm 9'daki kurulumla eklenir. CI benzeri, oturum bilgisi olmayan temiz tarayıcı testleri ve çapraz tarayıcı (Chromium/Firefox/WebKit) denemeleri için uygundur.

### C) `/run` ve `/verify`
Uygulamayı başlatıp değişikliği gerçekten çalışırken gözlemler. İlk kullanımda `/run-skill-generator` ile projenin nasıl başlatılacağını öğret.

### D) Desktop uygulamasının yerleşik tarayıcısı
Claude Code Desktop, yerel dev sunucusu önizlemeleri ve dokümanlar için uygulama içi tarayıcı içerir.

---

## 12. İzinler, güvenlik ve settings.json

### İzin modları (`Shift+Tab` ile geçiş)
| Mod | Değer | İzin istemeden çalışan | Ne zaman |
|---|---|---|---|
| Manuel | `default` | Yalnızca okuma | Her adımı kendin onaylamak için |
| Düzenlemeleri kabul | `acceptEdits` | Okuma, dosya düzenleme, `mkdir`/`mv`/`cp` gibi komutlar | İncelediğin kod üzerinde hızlı yineleme |
| Plan | `plan` | Okuma | Değişiklikten önce keşif ve plan |
| Otomatik | `auto` | Her şey, ama bir sınıflandırıcı model eylemleri önceden kontrol eder | Uzun görevler, az kesinti |
| Sorma | `dontAsk` | Yalnızca önceden izinli olanlar, gerisi reddedilir | CI ve script'ler |
| Atla | `bypassPermissions` | Her şey | **Yalnızca izole container/VM** |

Başlangıçta mod seçmek için: `claude --permission-mode plan`. **Deny kuralları her modda, `bypassPermissions` dahil, geçerlidir.**

### Önerilen `.claude/settings.json` (web projesi)

```json
{
  "permissions": {
    "allow": [
      "Bash(pnpm dev)",
      "Bash(pnpm typecheck)",
      "Bash(pnpm lint *)",
      "Bash(pnpm test *)",
      "Bash(pnpm build)",
      "Bash(git status *)",
      "Bash(git diff *)",
      "Bash(git log *)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(pnpm add *)",
      "Bash(pnpm db:migrate *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Edit(./.env*)",
      "Bash(rm -rf *)",
      "Bash(vercel --prod *)"
    ],
    "defaultMode": "acceptEdits"
  },
  "env": {
    "NODE_ENV": "development"
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/format-and-lint.sh" }
        ]
      }
    ]
  }
}
```

### Ayar dosyası öncelik sırası (yüksekten düşüğe)
Kurumsal managed → CLI bayrakları → `.claude/settings.local.json` → `.claude/settings.json` → `~/.claude/settings.json`

### Sandbox
`/sandbox` komutu, Bash komutlarının erişebileceği dosya ve ağ hostlarını kısıtlar. macOS, Linux ve WSL 2'de desteklenir, native Windows'ta desteklenmez. Daha güçlü izolasyon için dev container, Docker veya VM kullanabilirsin.

---

## 13. Paralel çalışma

| Yöntem | Ne zaman |
|---|---|
| **Alt ajanlar** | Ana görev sürerken araştırma, inceleme veya test yazma |
| **Git worktree** (`claude --worktree`) | Aynı repoda birden fazla özellik üzerinde çakışmasız paralel oturum |
| **`/fork`, `/subtask`** | Konuşmayı kopyalayıp yan görevi arka planda yürütme |
| **Agent view** (`claude agents`) | Tüm oturumları tek ekranda izleme: ne çalışıyor, ne seni bekliyor, ne bitti |
| **`/batch`** | Büyük çaplı refaktör veya migration'ı parçalara bölüp paralel uygulama |
| **Dinamik iş akışları (workflows)** | Onlarca–yüzlerce alt ajanı yöneten, Claude'un yazdığı script'ler (denetim, migration) |
| **Oturumlar arası mesajlaşma** | Bir oturumdaki bulguyu diğerine aktarma (`@oturum-adı`, `/list-agents`) |
| **Bulut oturumları** (`--cloud`, `/teleport`) | İşi buluta gönderme veya buluttan terminale çekme |

---

## 14. Kod inceleme ve kalite

- **`/code-review`**: Yerel diff'i doğruluk hataları için inceler. `--fix` ile düzeltmeleri uygular.
- **`/security-review`**: Branch'i güvenlik açıkları için tarar (`origin` remote'u gerekir).
- **`/simplify`**: Tekrar kullanım, sadeleştirme ve verimlilik için dört paralel ajan çalıştırır.
- **`/ultrareview`**: Bulutta çok ajanlı derin inceleme.
- **GitHub Actions:** `/install-github-app` ile kurulur. PR ve issue'larda `@claude` mention'larına yanıt verir ve issue'ları PR'a dönüştürür.
- **Code Review (Team/Enterprise):** GitHub PR'larını otomatik inceler ve satır içi yorum yapar. `REVIEW.md` ile özelleştirilir.
- **GitLab CI/CD** entegrasyonu da mevcuttur.

---

## 15. Otomasyon ve programatik kullanım

### Headless (etkileşimsiz) mod

```bash
claude -p "src/ altındaki tüm TODO yorumlarını listele"
claude -p "lint hatalarını düzelt" --permission-mode acceptEdits
cat build-error.log | claude -p "bu build hatasını açıkla"
```

### Zamanlama ve döngüler
- **`/loop 5m CI durumunu kontrol et ve kırılırsa düzelt`**: Oturum açıkken tekrarlar. Aralık verilmezse Claude kendisi ayarlar.
- **`/goal tüm e2e testleri geçsin`**: Koşul sağlanana kadar çalışmaya devam eder.
- **`/schedule`**: Bulutta zamanlanmış görev (ör. her sabah bağımlılık denetimi). Zamanlama, API çağrısı veya GitHub olayıyla tetiklenebilir.
- **Monitor aracı**: Arka plan loglarını (ör. dev sunucusu) canlı izleyip olaylara tepki verir.

### Agent SDK
Claude Code'u Python veya TypeScript kütüphanesi olarak kendi uygulamana gömebilirsin: özel araçlar, alt ajanlar, hook'lar, oturum yönetimi. [Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview)

### Deep link'ler
`claude-cli://` bağlantıları belirli bir repoda, hazır bir prompt'la oturum açar. README'ye "Claude ile başla" butonu koymak için kullanışlıdır.

---

## 16. Model, bağlam ve maliyet yönetimi

| Araç | Kullanım |
|---|---|
| `/model` | Model seçimi (Opus, Sonnet, Haiku…). Seçim yeni oturumlar için varsayılan olur |
| `/effort` | `low`, `medium`, `high`, `xhigh`, `max`, `auto`. Zor mimari kararlar için yükselt, rutin işler için düşür |
| `/fast` | Daha hızlı yanıt (ek ücretli) |
| `/advisor` | Kritik anlarda daha güçlü bir modele danışma |
| `/context` | Bağlamı neyin doldurduğunu gösterir |
| `/compact [odak]` | Konuşmayı özetler. Ör: `/compact auth refaktörüne odaklan` |
| `/clear` | Alakasız yeni bir göreve geçerken bağlamı sıfırla |
| `/usage` | Plan limitlerini neyin tükettiğini skill, alt ajan, eklenti ve MCP bazında gösterir |
| `/skill-doctor` | Skill'lerin bağlam maliyeti ve kullanım sıklığı |

**Bağlamı verimli kullanma ipuçları**
- Her yeni özelliğe `/clear` ile başla.
- Ağır araştırmayı alt ajanlara (Explore) devret, böylece sonuç özet olarak gelir.
- CLAUDE.md'yi kısa tut, ayrıntıyı path-scoped kurallara ve skill'lere taşı.
- Kullanmadığın MCP sunucularını `/mcp` ile kapat.

---

## 17. Önerilen web uygulaması iş akışı

### Aşama 1: Kurulum (bir kerelik)
```bash
# 1. Projeyi oluştur (ör. Next.js)
pnpm create next-app@latest acme-web --typescript --tailwind --app
cd acme-web && git init

# 2. Claude Code'u başlat ve CLAUDE.md üret
claude
> /init

# 3. Tip farkındalığı
npm install -g typescript-language-server typescript
> /plugin install typescript-lsp@claude-plugins-official

# 4. MCP sunucuları (ekip için --scope project)
claude mcp add --scope project playwright -- npx @playwright/mcp@latest
claude mcp add --scope project --transport http context7 https://mcp.context7.com/mcp
claude mcp add --scope project --transport http supabase https://mcp.supabase.com/mcp
claude mcp add --scope project --transport http vercel https://mcp.vercel.com
> /mcp     # OAuth girişlerini tamamla

# 5. İzinleri ve hook'ları ayarla (Bölüm 8 ve 12)
# 6. Skill'leri ve alt ajanları ekle (Bölüm 6 ve 7)
# 7. Her şeyi commit et: CLAUDE.md, .mcp.json, .claude/
```

### Aşama 2: Her özellik için döngü
1. **Planla:** `/plan kullanıcı profil sayfası ekle: avatar yükleme, ad/bio düzenleme`. Planı incele, düzelt, onayla.
2. **Tasarla (isteğe bağlı):** `/design profil sayfası` veya Figma MCP ile tasarımı çek.
3. **Uygula:** `acceptEdits` veya `auto` modunda bırak. Hook'lar format ve lint işini halleder, LSP tip hatalarını yakalar.
4. **Doğrula:** `localhost:3000/profile'ı Chrome'da aç ve akışı test et` veya `/verify`.
5. **Test et:** `test-writer alt ajanını kullan` veya `/goal tüm testler geçsin`.
6. **İncele:** `/code-review`, ardından `/security-review`.
7. **Commit / PR:** `değişiklikleri commit et ve PR aç` (gerekirse `gh` CLI veya GitHub MCP).
8. **Deploy:** `/deploy` (elle tetiklenen skill). Sorun çıkarsa Vercel ve Sentry MCP ile logları incele.

### Etkili prompt ipuçları
- Claude'un **göremediğini söyle:** "Bu hata yalnızca Safari'de oluyor", "Kullanıcılar mobilde şikâyet ediyor".
- **Kontrol edilebilir bir hedef ver:** "`pnpm test` geçene kadar devam et", "Lighthouse skoru 90'ın üstünde olsun".
- **Dosyaları referansla:** `@src/app/profile/page.tsx dosyasındaki form doğrulamasını düzelt`.
- **Görsel ver:** Ekran görüntüsünü sürükleyip bırak veya yapıştır ("Bunu şu mockup'a benzet").
- **Kesin kurallar için hook kullan,** CLAUDE.md'ye güvenme.

---

## 18. Hızlı başvuru: CLI komutları

```bash
claude                          # etkileşimli oturum
claude "prompt"                 # prompt ile başlat
claude -p "prompt"              # headless: yanıtı yazdır ve çık
claude -c                       # son konuşmaya devam et
claude -r                       # oturum seçici ile devam et
claude --permission-mode plan   # başlangıç izin modu
claude --chrome                 # Chrome entegrasyonuyla başlat
claude --worktree               # izole git worktree'de çalış
claude --agents '{...}'         # oturumluk alt ajanlar
claude --plugin-dir ./eklenti   # eklentiyi yerelden yükle
claude --safe-mode              # tüm özelleştirmeler kapalı (sorun giderme)
claude --cloud                  # bulut oturumu
claude agents                   # tüm oturumların görünümü
claude mcp add|list|get|remove|login|logout
claude plugin install <ad>@<marketplace>
claude doctor                   # teşhis
claude update                   # güncelle
```

**Önemli ortam değişkenleri**
| Değişken | Etki |
|---|---|
| `MAX_MCP_OUTPUT_TOKENS` | MCP çıktı sınırı |
| `MCP_TIMEOUT`, `MCP_TOOL_TIMEOUT` | MCP zaman aşımları (ms) |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | Eş zamanlı alt ajan sayısı (varsayılan 20) |
| `CLAUDE_CODE_NEW_INIT=1` | `/init` için etkileşimli çok aşamalı kurulum |
| `DISABLE_AUTOUPDATER=1` | Otomatik güncellemeyi kapatır |

---

## 19. Kaynaklar

- [Claude Code dokümantasyonu](https://code.claude.com/docs/en/overview) · [Tüm sayfaların dizini (llms.txt)](https://code.claude.com/docs/llms.txt)
- [Yenilikler (haftalık özet)](https://code.claude.com/docs/en/whats-new) · [Changelog](https://code.claude.com/docs/en/changelog)
- [Kurulum](https://code.claude.com/docs/en/setup) · [Özellik karşılaştırması: CLAUDE.md, skill, alt ajan, hook, MCP, eklenti](https://code.claude.com/docs/en/features-overview)
- [Hafıza / CLAUDE.md](https://code.claude.com/docs/en/memory) · [Skill'ler](https://code.claude.com/docs/en/skills) · [Alt ajanlar](https://code.claude.com/docs/en/sub-agents)
- [Hook'lar (referans)](https://code.claude.com/docs/en/hooks) · [Hook rehberi](https://code.claude.com/docs/en/hooks-guide)
- [MCP](https://code.claude.com/docs/en/mcp) · [Eklentiler](https://code.claude.com/docs/en/plugins/overview) · [Anthropic marketplace'leri](https://code.claude.com/docs/en/plugins/anthropic-marketplaces) · [Kod zekâsı (LSP) eklentileri](https://code.claude.com/docs/en/plugins/code-intelligence)
- [Komutlar](https://code.claude.com/docs/en/commands) · [CLI referansı](https://code.claude.com/docs/en/cli-reference) · [Ayarlar](https://code.claude.com/docs/en/settings) · [İzin modları](https://code.claude.com/docs/en/permission-modes)
- [Chrome ile kullanım](https://code.claude.com/docs/en/chrome) · [En iyi uygulamalar](https://code.claude.com/docs/en/best-practices) · [Yaygın iş akışları](https://code.claude.com/docs/en/common-workflows)
- MCP sunucuları: [Playwright MCP](https://github.com/microsoft/playwright-mcp) · [Context7](https://context7.com/docs/clients/claude-code) · [Supabase MCP](https://github.com/supabase-community/mcp-server-supabase) · [Vercel MCP](https://vercel.com/docs/ai-resources/vercel-mcp) · [Next.js DevTools MCP](https://github.com/vercel/next-devtools-mcp) · [Figma MCP](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation) · [shadcn MCP](https://ui.shadcn.com/docs/mcp) · [Sentry MCP](https://docs.sentry.io/product/sentry-mcp)
