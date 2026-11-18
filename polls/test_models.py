import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import Option, Poll, Vote

pytestmark = pytest.mark.django_db


@pytest.fixture
def author(django_user_model):
    return django_user_model.objects.create_user(
        email="yazar@example.com", username="yazar", password="Guclu-Parola-123"
    )


@pytest.fixture
def poll(author):
    poll = Poll.objects.create(author=author, question="Sinema mı restoran mı?")
    Option.objects.create(poll=poll, text="Sinema", position=0)
    Option.objects.create(poll=poll, text="Restoran", position=1)
    return poll


def test_polls_are_ordered_newest_first(author):
    first = Poll.objects.create(author=author, question="Birinci")
    second = Poll.objects.create(author=author, question="İkinci")
    assert list(Poll.objects.all()) == [second, first]


def test_options_are_ordered_by_position(author):
    poll = Poll.objects.create(author=author, question="Soru")
    Option.objects.create(poll=poll, text="C", position=2)
    Option.objects.create(poll=poll, text="A", position=0)
    Option.objects.create(poll=poll, text="B", position=1)
    assert [option.text for option in poll.options.all()] == ["A", "B", "C"]


def test_str_values_do_not_expose_email(poll, author):
    assert str(poll) == "Sinema mı restoran mı?"
    assert author.email not in str(poll)


def test_option_position_is_unique_per_poll(poll):
    with pytest.raises(IntegrityError), transaction.atomic():
        Option.objects.create(poll=poll, text="Tekrar", position=0)


def test_option_position_cannot_exceed_four(poll):
    with pytest.raises(IntegrityError), transaction.atomic():
        Option.objects.create(poll=poll, text="Altıncı", position=5)


def test_same_position_is_allowed_in_different_polls(poll, author):
    other = Poll.objects.create(author=author, question="Başka soru")
    Option.objects.create(poll=other, text="Sinema", position=0)


def test_user_can_vote_once_per_poll(poll, author):
    Vote.objects.create(poll=poll, option=poll.options.first(), user=author)
    with pytest.raises(IntegrityError), transaction.atomic():
        Vote.objects.create(poll=poll, option=poll.options.last(), user=author)


def test_anonymous_token_can_vote_once_per_poll(poll):
    token = uuid.uuid4()
    Vote.objects.create(poll=poll, option=poll.options.first(), voter_token=token)
    with pytest.raises(IntegrityError), transaction.atomic():
        Vote.objects.create(poll=poll, option=poll.options.last(), voter_token=token)


def test_same_voter_can_vote_in_different_polls(poll, author):
    other = Poll.objects.create(author=author, question="Başka soru")
    other_option = Option.objects.create(poll=other, text="Evet", position=0)
    Vote.objects.create(poll=poll, option=poll.options.first(), user=author)
    Vote.objects.create(poll=other, option=other_option, user=author)


def test_different_voters_can_vote_on_same_poll(poll, author):
    Vote.objects.create(poll=poll, option=poll.options.first(), user=author)
    Vote.objects.create(poll=poll, option=poll.options.first(), voter_token=uuid.uuid4())
    Vote.objects.create(poll=poll, option=poll.options.first(), voter_token=uuid.uuid4())
    assert poll.votes.count() == 3


def test_vote_requires_a_voter(poll):
    with pytest.raises(IntegrityError), transaction.atomic():
        Vote.objects.create(poll=poll, option=poll.options.first())


def test_vote_clean_rejects_option_from_another_poll(poll, author):
    other = Poll.objects.create(author=author, question="Başka soru")
    foreign_option = Option.objects.create(poll=other, text="Evet", position=0)
    vote = Vote(poll=poll, option=foreign_option, user=author)
    with pytest.raises(ValidationError):
        vote.clean()


def test_deleting_poll_removes_options_and_votes(poll, author):
    Vote.objects.create(poll=poll, option=poll.options.first(), user=author)
    poll.delete()
    assert not Option.objects.exists()
    assert not Vote.objects.exists()


def test_deleting_author_removes_their_polls(poll, author):
    author.delete()
    assert not Poll.objects.exists()
