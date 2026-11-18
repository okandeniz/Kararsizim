from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

QUESTION_MAX_LENGTH = 200
OPTION_MAX_LENGTH = 80
MIN_OPTIONS = 2
MAX_OPTIONS = 5


class Poll(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="polls",
        verbose_name="yazar",
    )
    question = models.CharField("soru", max_length=QUESTION_MAX_LENGTH)
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "anket"
        verbose_name_plural = "anketler"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.question


class Option(models.Model):
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name="options", verbose_name="anket"
    )
    text = models.CharField("metin", max_length=OPTION_MAX_LENGTH)
    # 0–4: seçenek rengi (--c1…--c5) ve sıralama bu değere göre belirlenir.
    position = models.PositiveSmallIntegerField("sıra")

    class Meta:
        verbose_name = "seçenek"
        verbose_name_plural = "seçenekler"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["poll", "position"], name="unique_option_position"),
            models.CheckConstraint(
                condition=models.Q(position__lt=MAX_OPTIONS),
                name="option_position_range",
            ),
        ]

    def __str__(self):
        return self.text


class Vote(models.Model):
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name="votes", verbose_name="anket"
    )
    option = models.ForeignKey(
        Option, on_delete=models.CASCADE, related_name="votes", verbose_name="seçenek"
    )
    # Üye oyu: user dolu. Anonim oy: imzalı çerezdeki voter_token dolu.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="üye",
    )
    voter_token = models.UUIDField("anonim oy sahibi", null=True, blank=True)
    created_at = models.DateTimeField("oy zamanı", auto_now_add=True)

    class Meta:
        verbose_name = "oy"
        verbose_name_plural = "oylar"
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

    def __str__(self):
        return f"{self.poll_id} → {self.option_id}"

    def clean(self):
        super().clean()
        if self.option_id and self.poll_id and self.option.poll_id != self.poll_id:
            raise ValidationError("Seçenek bu ankete ait değil.")
