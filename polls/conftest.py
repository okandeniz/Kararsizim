import pytest

from .models import Option, Poll

PASSWORD = "Guclu-Parola-123"


@pytest.fixture
def author(django_user_model):
    return django_user_model.objects.create_user(
        email="yazar@example.com", username="yazar", password=PASSWORD
    )


@pytest.fixture
def make_poll(author):
    """Anket + seçenek oluşturan fabrika. Seçenekler verilen sırayla position 0..n-1 alır."""

    def factory(question="Hangisi?", options=("Kırmızı", "Mavi", "Yeşil"), poll_author=None):
        poll = Poll.objects.create(author=poll_author or author, question=question)
        Option.objects.bulk_create(
            Option(poll=poll, text=text, position=position) for position, text in enumerate(options)
        )
        return poll

    return factory


@pytest.fixture
def poll(make_poll):
    return make_poll()
