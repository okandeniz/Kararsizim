import pytest
from django.forms import inlineformset_factory

from .admin import OptionInlineFormSet
from .models import Option, Poll

pytestmark = pytest.mark.django_db

OptionFormSet = inlineformset_factory(
    Poll, Option, formset=OptionInlineFormSet, fields=("text", "position"), extra=0, can_delete=True
)


def formset_data(texts, initial=0, deleted=()):
    data = {
        "options-TOTAL_FORMS": len(texts),
        "options-INITIAL_FORMS": initial,
        "options-MIN_NUM_FORMS": 0,
        "options-MAX_NUM_FORMS": 1000,
    }
    for index, text in enumerate(texts):
        data[f"options-{index}-text"] = text
        data[f"options-{index}-position"] = index
        if index in deleted:
            data[f"options-{index}-DELETE"] = "on"
    return data


@pytest.mark.parametrize("count", [2, 3, 5])
def test_admin_accepts_two_to_five_options(author, count):
    poll = Poll.objects.create(author=author, question="Soru")
    formset = OptionFormSet(formset_data([f"Seçenek {i}" for i in range(count)]), instance=poll)
    assert formset.is_valid(), formset.non_form_errors()


@pytest.mark.parametrize("count", [0, 1])
def test_admin_rejects_fewer_than_two_options(author, count):
    poll = Poll.objects.create(author=author, question="Soru")
    formset = OptionFormSet(formset_data([f"Seçenek {i}" for i in range(count)]), instance=poll)

    assert not formset.is_valid()
    assert "2 ile 5 arası" in str(formset.non_form_errors())


def test_admin_rejects_six_options(author):
    # 6. seçenek 0–4 dışında bir sıra veya tekrar eden sıra almak zorunda: veritabanı kısıtları
    # form doğrulamasında da devreye girer; formset kuralı ise ek güvence verir.
    poll = Poll.objects.create(author=author, question="Soru")
    formset = OptionFormSet(formset_data([f"Seçenek {i}" for i in range(6)]), instance=poll)

    assert not formset.is_valid()


def test_admin_rejects_deleting_options_below_the_minimum(make_poll):
    poll = make_poll(options=("A", "B", "C"))
    data = formset_data(["A", "B", "C"], initial=3, deleted=(1, 2))
    for index, option in enumerate(poll.options.all()):
        data[f"options-{index}-id"] = option.pk
        data[f"options-{index}-poll"] = poll.pk
    formset = OptionFormSet(data, instance=poll)

    assert not formset.is_valid()
    assert "2 ile 5 arası" in str(formset.non_form_errors())
