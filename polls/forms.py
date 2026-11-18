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


def normalize_text(value: str) -> str:
    """Baştaki/sondaki boşlukları kırpar, aradaki boşluk/satır sonlarını tek boşluğa indirir."""
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
        return normalize_text(self.cleaned_data["question"])

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
