---
name: auth-review-patterns
description: Kararsizim Faz 2 incelemesinde bulunan tekrar eden auth/form sorunları ve bilinçli ürün kararları
metadata:
  type: project
---

Bilinçli karar (bulgu sayma): kayıtta e-posta çakışması mesajı ("Bu e-posta ile zaten bir hesap var.") gösterilir.

Faz 2'de görülen tekrar eden sorunlar (sonraki fazlarda da kontrol et):
- ModelForm save() çevresinde IntegrityError yakalanmıyor (RegisterView.form_valid) -> yarışta 500. Anket/oy akışında da aynı kalıp aranmalı.
- Benzersizlik yalnızca formda/save()'de büyük-küçük harf duyarsız; DB'de email için Lower() kısıtı yok (username için var).
- Regex `^...$` kullanımı (sonda \n kabul eder); `\Z` tercih edilmeli.
- Giriş/kayıt için rate limit yok.
- LoginView redirect_authenticated_user=True + `?next=/giris/` -> ValueError (500).
- settings.py'deki `MAILERS` Django ayarı değil (ölü yapılandırma; EMAIL_BACKEND olmalı).

Doğrulanan iyi uygulamalar: safe_next_url (url_has_allowed_host_and_scheme), logout POST+csrf, genel giriş hata mesajı, User.__str__ username döndürüyor, şablonlarda |safe yok.

**How to apply:** Faz 3+ incelemesinde aynı kalıpları (IntegrityError, harf duyarlılığı, next kontrolü) yeni görünümlerde ara.
