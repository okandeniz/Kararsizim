"""Sayfa iskeleti: favicon, paylaşım önizlemesi (Open Graph) ve erişilebilirlik işaretleri."""

import re
from pathlib import Path

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

STATIC = Path(__file__).resolve().parent.parent / "static"


def detail_url(poll):
    return reverse("polls:detail", kwargs={"pk": poll.pk})


# ---------- Favicon ve Open Graph ----------


def test_head_links_the_svg_favicon(client):
    body = client.get(reverse("polls:feed")).content.decode()
    assert 'rel="icon"' in body
    assert "img/favicon.svg" in body


def test_favicon_file_is_a_gradient_svg():
    svg = (STATIC / "img" / "favicon.svg").read_text(encoding="utf-8")

    assert svg.lstrip().startswith("<svg")
    assert "linearGradient" in svg


def test_every_page_has_basic_open_graph_tags(client):
    body = client.get(reverse("polls:feed")).content.decode()

    for prop in ("og:site_name", "og:type", "og:locale", "og:title", "og:description", "og:url"):
        assert f'property="{prop}"' in body
    assert 'content="http://testserver/"' in body
    assert 'name="twitter:card"' in body


def test_detail_page_shares_question_and_options_without_email(client, poll):
    body = client.get(detail_url(poll)).content.decode()

    assert f'property="og:title" content="{poll.question}"' in body
    assert "Kırmızı · Mavi · Yeşil" in body
    assert "@yazar kararsız kaldı" in body
    assert "Sen ne dersin?" in body
    assert "yazar@example.com" not in body


def test_detail_share_description_is_in_both_meta_tags(client, poll):
    body = client.get(detail_url(poll)).content.decode()

    assert body.count("@yazar kararsız kaldı: Kırmızı · Mavi · Yeşil (0 oy). Sen ne dersin?") == 2


def test_open_graph_attributes_escape_user_content(client, make_poll):
    poll = make_poll(question='"><script>alert(1)</script>', options=('a"b', "<i>x</i>"))
    body = client.get(detail_url(poll)).content.decode()

    assert '"><script>alert(1)</script>' not in body
    assert "&quot;&gt;&lt;script&gt;" in body
    assert "<i>x</i>" not in body


# ---------- Erişilebilirlik ----------


def test_skip_link_targets_the_main_landmark(client):
    body = client.get(reverse("polls:feed")).content.decode()

    assert 'class="skip-link" href="#main"' in body
    assert 'id="main"' in body


def test_header_create_button_keeps_its_name_when_text_is_hidden(client):
    body = client.get(reverse("polls:feed")).content.decode()

    assert 'aria-label="Anket oluştur"' in body
    assert "btn--create__icon" in body  # mobilde "+" ikonu
    assert "btn--create__text" in body  # masaüstünde metin


def test_feed_has_a_heading_for_screen_readers(client, poll):
    assert '<h1 class="sr-only">Anketler</h1>' in client.get(reverse("polls:feed")).content.decode()


def test_share_link_is_a_large_touch_target(client, poll):
    assert 'class="poll-card__share"' in client.get(reverse("polls:feed")).content.decode()


def test_detail_page_has_exactly_one_h1(client, poll):
    assert client.get(detail_url(poll)).content.decode().count("<h1") == 1


def test_feed_has_exactly_one_h1(client, poll):
    assert client.get(reverse("polls:feed")).content.decode().count("<h1") == 1


# ---------- İncelemeden gelen iyileştirmeler ----------


def test_og_url_drops_the_query_string(client):
    body = client.get(reverse("polls:feed"), {"page": 1, "utm_source": "x"}).content.decode()
    assert 'property="og:url" content="http://testserver/"' in body


def test_og_description_stays_short_with_five_long_options(client, make_poll):
    poll = make_poll(options=("a" * 80, "b" * 80, "c" * 80, "d" * 80, "e" * 80))
    body = client.get(detail_url(poll)).content.decode()
    description = re.search(r'property="og:description" content="([^"]*)"', body).group(1)

    assert len(description) < 320
    assert "…" in description  # her seçenek 40 karakterde kısaltılır


def test_share_link_names_its_poll_for_screen_readers(client, poll):
    body = client.get(reverse("polls:feed")).content.decode()
    assert 'Paylaş<span class="sr-only">: Hangisi?</span>' in body


def test_option_errors_are_linked_to_the_fieldset(client, django_user_model):
    member = django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password="Guclu-Parola-123"
    )
    client.force_login(member)

    body = client.post(
        reverse("polls:create"), {"question": "Soru", "option": ["Tek"]}
    ).content.decode()

    assert 'aria-describedby="options-errors"' in body
    assert 'id="options-errors"' in body


def test_option_fieldset_has_no_description_link_without_errors(client, django_user_model):
    member = django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password="Guclu-Parola-123"
    )
    client.force_login(member)

    assert "aria-describedby" not in client.get(reverse("polls:create")).content.decode()
