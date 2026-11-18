import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .conftest import PASSWORD
from .models import Option, Poll, Vote

pytestmark = pytest.mark.django_db

FEED_URL = reverse("polls:feed")


def vote_url(poll):
    return reverse("polls:vote", kwargs={"pk": poll.pk})


def option_id(poll, position=0):
    return poll.options.all()[position].pk


def make_many(make_poll, count, options=("A", "B", "C")):
    return [make_poll(question=f"Soru {i}", options=options) for i in range(1, count + 1)]


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password=PASSWORD
    )


# ---------- Boş durum ve temel içerik ----------


def test_empty_feed_shows_empty_state_with_create_button(client):
    response = client.get(FEED_URL)
    body = response.content.decode()

    assert response.status_code == 200
    assert "Henüz anket yok." in body
    assert "İlk kararsızlığı sen paylaş!" in body
    assert f'href="{reverse("polls:create")}"' in body
    assert "pagination" not in body


def test_feed_shows_all_polls_newest_first(client, make_poll):
    make_poll(question="Eski anket")
    make_poll(question="Yeni anket")
    body = client.get(FEED_URL).content.decode()

    assert body.index("Yeni anket") < body.index("Eski anket")
    assert "Henüz anket yok." not in body


def test_feed_shows_polls_of_all_authors(client, make_poll, member):
    make_poll(question="Yazarın anketi")
    make_poll(question="Üyenin anketi", poll_author=member)
    body = client.get(FEED_URL).content.decode()

    assert "Yazarın anketi" in body
    assert "Üyenin anketi" in body
    assert "@yazar" in body
    assert "@uye" in body


def test_feed_never_exposes_emails(client, make_poll, member):
    make_poll()
    client.force_login(member)
    body = client.get(FEED_URL).content.decode()

    assert "yazar@example.com" not in body
    assert "uye@example.com" not in body


def test_card_has_share_link_and_total_votes(client, poll):
    body = client.get(FEED_URL).content.decode()

    assert reverse("polls:detail", kwargs={"pk": poll.pk}) in body
    assert "Paylaş" in body
    assert "0 oy" in body


def test_card_options_have_color_positions(client, poll):
    body = client.get(FEED_URL).content.decode()
    for number in (1, 2, 3):
        assert f'data-position="{number}"' in body


# ---------- Oy durumuna göre kart ----------


def test_voted_poll_shows_results_and_others_show_form(client, make_poll):
    voted, unvoted = make_poll(question="Oy verilen"), make_poll(question="Oy verilmeyen")
    client.post(vote_url(voted), {"option": option_id(voted)})
    response = client.get(FEED_URL)
    polls = {poll.question: poll for poll in response.context["polls"]}

    assert polls["Oy verilen"].has_voted
    assert not polls["Oy verilmeyen"].has_voted
    body = response.content.decode()
    assert body.count("data-results") == 1
    assert body.count("data-vote-form") == 1
    del unvoted


def test_results_persist_after_reload_for_anonymous_voter(client, poll):
    client.post(vote_url(poll), {"option": option_id(poll, 1)})
    for _ in range(2):  # sayfa yenilenince sonuçlar görünmeye devam eder
        body = client.get(FEED_URL).content.decode()
        assert "data-results" in body
        assert "result--chosen" in body


def test_other_visitors_do_not_see_my_choice(client, poll):
    Client().post(vote_url(poll), {"option": option_id(poll)})
    body = client.get(FEED_URL).content.decode()

    assert "data-vote-form" in body
    assert "result--chosen" not in body


def test_vote_counts_are_shown_per_option(client, poll):
    for position in (0, 0, 1):
        Client().post(vote_url(poll), {"option": option_id(poll, position)})
    client.post(vote_url(poll), {"option": option_id(poll, 0)})
    body = client.get(FEED_URL).content.decode()

    assert "%75 · 3 oy" in body
    assert "%25 · 1 oy" in body
    assert "4 oy" in body


def test_vote_form_carries_next_with_page_and_anchor(client, poll):
    body = client.get(FEED_URL, {"page": 1}).content.decode()
    assert f'name="next" value="/?page=1#poll-{poll.pk}"' in body


# ---------- Sayfalama ----------


def test_feed_paginates_by_twenty(client, make_poll):
    make_many(make_poll, 25, options=("A", "B"))

    first = client.get(FEED_URL)
    second = client.get(FEED_URL, {"page": 2})

    assert len(first.context["polls"]) == 20
    assert len(second.context["polls"]) == 5
    assert [poll.question for poll in first.context["polls"]][:2] == ["Soru 25", "Soru 24"]
    assert [poll.question for poll in second.context["polls"]] == [
        f"Soru {i}" for i in range(5, 0, -1)
    ]
    assert "Soru 25" not in second.content.decode()


def test_pagination_links(client, make_poll):
    make_many(make_poll, 25, options=("A", "B"))

    first = client.get(FEED_URL).content.decode()
    second = client.get(FEED_URL, {"page": 2}).content.decode()

    assert 'href="?page=2"' in first
    assert "Sonraki" in first
    assert "Önceki" not in first
    assert 'href="?page=1"' in second
    assert "Önceki" in second
    assert "Sonraki" not in second
    assert "Sayfa 2 / 2" in second


def test_no_pagination_for_single_page(client, make_poll):
    make_many(make_poll, 3, options=("A", "B"))
    assert "Sayfalama" not in client.get(FEED_URL).content.decode()


@pytest.mark.parametrize(
    # Sayı olmayan değer → 1. sayfa; aralık dışı (0, negatif, çok büyük) → son sayfa.
    ("page", "expected_polls"),
    [("abc", 20), ("", 20), ("0", 5), ("-3", 5), ("999", 5)],
)
def test_invalid_page_numbers_fall_back_gracefully(client, make_poll, page, expected_polls):
    make_many(make_poll, 25, options=("A", "B"))
    response = client.get(FEED_URL, {"page": page})

    assert response.status_code == 200
    assert len(response.context["polls"]) == expected_polls


# ---------- Sorgu verimliliği (N+1 yok) ----------


def count_queries(client, url="/"):
    with CaptureQueriesContext(connection) as context:
        response = client.get(url)
    assert response.status_code == 200
    return len(context)


def test_feed_query_count_does_not_grow_with_poll_count(make_poll):
    make_poll(question="Tek")
    few = count_queries(Client())

    make_many(make_poll, 19, options=("A", "B", "C", "D", "E"))
    many = count_queries(Client())

    assert many == few


def test_feed_query_count_is_constant_for_member_with_votes(make_poll, member):
    polls = make_many(make_poll, 3)
    client = Client()
    client.force_login(member)
    few = count_queries(client)

    polls += make_many(make_poll, 17)
    for poll in polls:
        Vote.objects.create(poll=poll, option=poll.options.first(), user=member)
    many = count_queries(client)

    assert many == few  # üyenin oyları anket sayısından bağımsız tek sorguyla bulunur


def test_feed_query_count_is_constant_for_anonymous_voter(make_poll):
    polls = make_many(make_poll, 20)
    client = Client()
    client.post(vote_url(polls[0]), {"option": option_id(polls[0])})
    baseline = count_queries(client)

    for poll in polls[1:10]:
        client.post(vote_url(poll), {"option": option_id(poll)})

    assert count_queries(client) == baseline


def test_feed_uses_a_small_fixed_number_of_queries(make_poll, django_assert_max_num_queries):
    make_many(make_poll, 20, options=("A", "B", "C", "D", "E"))
    client = Client()
    client.post(vote_url(Poll.objects.first()), {"option": Option.objects.first().pk})

    with django_assert_max_num_queries(5):  # sayım + anketler + seçenekler + oylar
        client.get(FEED_URL)
