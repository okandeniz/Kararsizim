import unicodedata

from django import forms
from django.db import transaction

from .models import (
    MAX_OPTIONS,
    MIN_OPTIONS,
    OPTION_MAX_LENGTH,
    QUESTION_MAX_LENGTH,
    Option,
    Poll,
)

# Görünmez veya yönü değiştiren karakterler. ZWJ/ZWNJ (U+200D/U+200C) bilerek yok: emoji dizileri
# (👨‍👩‍👧) ve bazı yazı sistemleri bunlara ihtiyaç duyar.
INVISIBLE_CHARS = frozenset(
    {"​", "⁠", "﻿"}  # sıfır genişlikli boşluk, word joiner, BOM
    | {chr(code) for code in range(0x202A, 0x202F)}  # çift yönlü gömme/geçersiz kılma
    | {chr(code) for code in range(0x2066, 0x206A)}  # çift yönlü izolasyon
)


def normalize_text(value: str) -> str:
    """Kullanıcı metnini kaydedilebilir hale getirir.

    - NFC'ye çevirir (bileşik/ayrık aksan farkı tekrar denetimini atlatamaz).
    - NUL ve diğer kontrol karakterlerini (Postgres NUL'u reddeder) ve görünmez/yön değiştiren
      karakterleri siler. Boşluk benzeri karakterler (satır sonu, sekme) korunur.
    - Baştaki/sondaki boşlukları kırpar, aradaki boşlukları tek boşluğa indirir.
    """
    value = unicodedata.normalize("NFC", value)
    value = "".join(
        char
        for char in value
        if char.isspace() or (unicodedata.category(char) != "Cc" and char not in INVISIBLE_CHARS)
    )
    return " ".join(value.split())


class PollForm(forms.Form):
    """Soru + 2–5 seçenek. Tüm doğrulamalar burada, sunucu tarafında yapılır.

    Seçenekler HTML'de aynı adlı (`option`) 5 ayrı input olarak gelir. Boş olanlar yok sayılır.
    """

    question = forms.CharField(
        label="Sorun ne?",
        max_length=QUESTION_MAX_LENGTH,
        error_messages={
            "required": "Sorunu yazmayı unutma.",
            "max_length": f"Soru en fazla {QUESTION_MAX_LENGTH} karakter olabilir.",
        },
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Örn. Bugün sinemaya mı gitsem, restorana mı?",
                "autocomplete": "off",
                "data-counted": "",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raw_options = self.data.getlist("option") if self.is_bound else []

    def clean_question(self):
        question = normalize_text(self.cleaned_data["question"])
        if not question:
            # Yalnızca görünmez karakterlerden oluşan soru, görünürde boştur.
            raise forms.ValidationError(self.fields["question"].error_messages["required"])
        if len(question) > QUESTION_MAX_LENGTH:
            # CharField sınırı ham metne uygulanır; NFC bazı karakterleri uzatır (1 → 2). Postgres
            # "value too long" ile reddeder (SQLite etmez): normalize sonrası da denetlenir.
            raise forms.ValidationError(self.fields["question"].error_messages["max_length"])
        return question

    def clean(self):
        cleaned_data = super().clean()

        options = [text for text in map(normalize_text, self.raw_options) if text]
        errors = []

        if len(options) < MIN_OPTIONS:
            errors.append(f"En az {MIN_OPTIONS} seçenek yazmalısın.")
        elif len(options) > MAX_OPTIONS:
            errors.append(f"En fazla {MAX_OPTIONS} seçenek ekleyebilirsin.")
        if any(len(text) > OPTION_MAX_LENGTH for text in options):
            errors.append(f"Her seçenek en fazla {OPTION_MAX_LENGTH} karakter olabilir.")
        if len({text.casefold() for text in options}) != len(options):
            errors.append("Aynı seçeneği iki kez yazdın.")

        for message in errors:
            self.add_error(None, message)
        cleaned_data["options"] = options
        return cleaned_data

    @property
    def option_slots(self) -> list[dict]:
        """Şablon için her zaman MAX_OPTIONS adet giriş kutusu; hatada girilen değerler korunur."""
        values = (self.raw_options + [""] * MAX_OPTIONS)[:MAX_OPTIONS]
        return [
            {"number": index + 1, "value": value, "required": index < MIN_OPTIONS}
            for index, value in enumerate(values)
        ]

    def save(self, author) -> Poll:
        with transaction.atomic():
            poll = Poll.objects.create(author=author, question=self.cleaned_data["question"])
            Option.objects.bulk_create(
                Option(poll=poll, text=text, position=position)
                for position, text in enumerate(self.cleaned_data["options"])
            )
        return poll
