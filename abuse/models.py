from django.db import models
from django.utils import timezone


class Hit(models.Model):
    """Hız sınırı sayacı: bir kapsamda (oy, kayıt, giriş...) bir öznenin tek isteği.

    Ham IP veya e-posta ASLA saklanmaz; `subject` bir HMAC özetidir (abuse/identity.py). Kayıtlar
    en geç 25 saat sonra silinir (abuse/limits.py `purge_old`). Vercel serverless olduğu için
    sayaçlar bellekte değil veritabanında tutulur.
    """

    scope = models.CharField("kapsam", max_length=64)
    subject = models.CharField("özne (özet)", max_length=64)
    created_at = models.DateTimeField("zaman", default=timezone.now)

    class Meta:
        verbose_name = "istek kaydı"
        verbose_name_plural = "istek kayıtları"
        indexes = [
            models.Index(fields=["scope", "subject", "created_at"], name="abuse_hit_lookup"),
            models.Index(fields=["created_at"], name="abuse_hit_created"),
        ]

    def __str__(self):
        return f"{self.scope} {self.subject[:8]}"
