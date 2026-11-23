import pytest
from django.urls import reverse

from .models import Option, Poll

pytestmark = pytest.mark.django_db

PASSWORD = "Guclu-Parola-123"
CREATE_URL = reverse("polls:create")
LOGIN_URL = reverse("accounts:login")


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="uye@example.com", username="uye", password=PASSWORD
    )


@pytest.fixture
def member_client(client, member):
    client.force_login(member)
    return client


def post_poll(client, question="Sinema mı restoran mı?", options=("Sinema", "Restoran"), **extra):
    data = {"question": question, "option": list(options), **extra}
    return client.post(CREATE_URL, data)


def option_texts(poll):
    return [option.text for option in poll.options.all()]


# ---------- Erişim ----------


def test_guest_is_redirected_to_login_with_next(client):
    response = client.get(CREATE_URL)

    assert response.status_code == 302
    assert response.url == f"{LOGIN_URL}?next={CREATE_URL}"


def test_guest_sees_login_required_message_on_login_page(client):
    response = client.get(CREATE_URL, follow=True)

    assert response.redirect_chain[-1][0] == f"{LOGIN_URL}?next={CREATE_URL}"
    assert "Anket oluşturmak için giriş yapmalısın." in response.content.decode()


def test_guest_post_does_not_create_poll(client):
    response = post_poll(client)

    assert response.status_code == 302
    assert response.url.startswith(LOGIN_URL)
    assert not Poll.objects.exists()


def test_after_login_user_returns_to_create_form(client, member):
    response = client.post(
        LOGIN_URL, {"username": "uye@example.com", "password": PASSWORD, "next": CREATE_URL}
    )
    assert response.url == CREATE_URL
    assert client.get(CREATE_URL).status_code == 200


def test_header_create_button_links_to_create_page(client, member):
    for logged_in in (False, True):
        if logged_in:
            client.force_login(member)
        body = client.get(reverse("polls:feed")).content.decode()
        assert f'href="{CREATE_URL}"' in body


# ---------- Form görünümü ----------


def test_form_renders_five_option_inputs_and_csrf(member_client):
    body = member_client.get(CREATE_URL).content.decode()

    assert body.count('name="option"') == 5
    assert "csrfmiddlewaretoken" in body
    assert 'name="question"' in body
    assert 'maxlength="200"' in body
    assert 'maxlength="80"' in body


def test_only_first_two_options_are_required(member_client):
    response = member_client.get(CREATE_URL)
    slots = response.context["form"].option_slots

    assert [slot["required"] for slot in slots] == [True, True, False, False, False]


# ---------- Başarılı oluşturma ----------


@pytest.mark.parametrize("count", [2, 3, 4, 5])
def test_create_with_valid_option_counts(member_client, member, count):
    options = [f"Seçenek {i}" for i in range(1, count + 1)]
    response = post_poll(member_client, options=options)

    poll = Poll.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("polls:detail", kwargs={"pk": poll.pk})
    assert poll.author == member
    assert option_texts(poll) == options
    assert [option.position for option in poll.options.all()] == list(range(count))


def test_success_message_is_shown_on_detail_page(member_client):
    response = member_client.post(
        CREATE_URL, {"question": "Soru", "option": ["A", "B"]}, follow=True
    )
    assert "Anketin yayında!" in response.content.decode()


def test_blank_options_are_dropped_and_positions_are_contiguous(member_client):
    post_poll(member_client, options=["A", "", "B", "   ", "C"])

    poll = Poll.objects.get()
    assert option_texts(poll) == ["A", "B", "C"]
    assert [option.position for option in poll.options.all()] == [0, 1, 2]


def test_texts_are_trimmed_and_inner_whitespace_collapsed(member_client):
    post_poll(member_client, question="  Bugün   ne\nyapsam?  ", options=["  Evet  ", "Belki\t de"])

    poll = Poll.objects.get()
    assert poll.question == "Bugün ne yapsam?"
    assert option_texts(poll) == ["Evet", "Belki de"]


def test_boundary_lengths_are_accepted(member_client):
    post_poll(member_client, question="s" * 200, options=["a" * 80, "b" * 80])

    poll = Poll.objects.get()
    assert len(poll.question) == 200
    assert [len(text) for text in option_texts(poll)] == [80, 80]


def test_author_cannot_be_forged_via_post(member_client, member, django_user_model):
    other = django_user_model.objects.create_user(
        email="baska@example.com", username="baska", password=PASSWORD
    )
    post_poll(member_client, author=other.pk)

    assert Poll.objects.get().author == member


# ---------- Doğrulama hataları ----------


def assert_rejected(client, response, message):
    assert response.status_code == 200
    assert message in response.content.decode()
    assert not Poll.objects.exists()
    assert not Option.objects.exists()


def test_one_option_is_rejected(member_client):
    response = post_poll(member_client, options=["Sadece biri", "", "", "", ""])
    assert_rejected(member_client, response, "En az 2 seçenek yazmalısın.")


def test_no_options_is_rejected(member_client):
    response = post_poll(member_client, options=["", "", "", "", ""])
    assert_rejected(member_client, response, "En az 2 seçenek yazmalısın.")


def test_blank_only_options_do_not_count(member_client):
    response = post_poll(member_client, options=["A", "   ", "\t", "", ""])
    assert_rejected(member_client, response, "En az 2 seçenek yazmalısın.")


def test_six_options_via_post_manipulation_is_rejected(member_client):
    response = post_poll(member_client, options=["1", "2", "3", "4", "5", "6"])
    assert_rejected(member_client, response, "En fazla 5 seçenek ekleyebilirsin.")


def test_duplicate_options_are_rejected_case_insensitively(member_client):
    response = post_poll(member_client, options=["Evet", "evet", "Hayır"])
    assert_rejected(member_client, response, "Aynı seçeneği iki kez yazdın.")


def test_duplicate_options_ignore_whitespace_differences(member_client):
    response = post_poll(member_client, options=["Çok iyi", "çok   iyi"])
    assert_rejected(member_client, response, "Aynı seçeneği iki kez yazdın.")


def test_empty_question_is_rejected(member_client):
    response = post_poll(member_client, question="")
    assert_rejected(member_client, response, "Sorunu yazmayı unutma.")


def test_whitespace_only_question_is_rejected(member_client):
    response = post_poll(member_client, question="    ")
    assert_rejected(member_client, response, "Sorunu yazmayı unutma.")


def test_question_longer_than_200_is_rejected(member_client):
    response = post_poll(member_client, question="s" * 201)
    assert_rejected(member_client, response, "Soru en fazla 200 karakter olabilir.")


def test_option_longer_than_80_is_rejected(member_client):
    response = post_poll(member_client, options=["a" * 81, "kısa"])
    assert_rejected(member_client, response, "Her seçenek en fazla 80 karakter olabilir.")


def test_entered_values_are_preserved_on_error(member_client):
    response = post_poll(
        member_client, question="Korunan soru", options=["Korunan A", "", "", "", ""]
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert 'value="Korunan soru"' in body
    assert 'value="Korunan A"' in body
    assert "En az 2 seçenek yazmalısın." in body


def test_option_values_keep_their_slots_on_error(member_client):
    response = post_poll(member_client, options=["Birinci", "Birinci", "", "", "Beşinci"])
    slots = response.context["form"].option_slots

    assert [slot["value"] for slot in slots] == ["Birinci", "Birinci", "", "", "Beşinci"]


def test_atomicity_poll_is_not_saved_if_options_fail(member_client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("seçenekler kaydedilemedi")

    monkeypatch.setattr(Option.objects, "bulk_create", boom)
    with pytest.raises(RuntimeError):
        post_poll(member_client)

    assert not Poll.objects.exists()


# ---------- Detay sayfası ----------


@pytest.fixture
def poll(member):
    poll = Poll.objects.create(author=member, question="Hangisi?")
    for position, text in enumerate(["Kırmızı", "Mavi", "Yeşil"]):
        Option.objects.create(poll=poll, text=text, position=position)
    return poll


def detail_url(poll):
    return reverse("polls:detail", kwargs={"pk": poll.pk})


def test_detail_shows_question_author_and_options_in_order(client, poll):
    response = client.get(detail_url(poll))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Hangisi?" in body
    assert "@uye" in body
    assert body.index("Kırmızı") < body.index("Mavi") < body.index("Yeşil")
    assert "<title>Hangisi? — kararsızım</title>" in body


def test_detail_does_not_expose_author_email(client, poll):
    assert "uye@example.com" not in client.get(detail_url(poll)).content.decode()


def test_detail_is_public(client, poll):
    assert client.get(detail_url(poll)).status_code == 200


def test_detail_unknown_poll_returns_404(client):
    assert client.get(reverse("polls:detail", kwargs={"pk": 9999})).status_code == 404


def test_detail_escapes_html_in_user_content(client, member):
    poll = Poll.objects.create(author=member, question="<script>alert(1)</script>")
    Option.objects.create(poll=poll, text="<b>kalın</b>", position=0)
    Option.objects.create(poll=poll, text="normal", position=1)
    body = client.get(detail_url(poll)).content.decode()

    assert "<script>alert(1)</script>" not in body
    assert "<b>kalın</b>" not in body
    assert "&lt;script&gt;" in body


def test_detail_uses_constant_number_of_queries(client, poll, django_assert_max_num_queries):
    with django_assert_max_num_queries(4):
        client.get(detail_url(poll))


# ---------- Görünmez / kontrol karakterleri (incelemeden) ----------


def test_nul_and_control_characters_are_stripped_from_options(member_client):
    # Postgres NUL'u reddeder (500); SQLite kabul eder, bu yüzden metin kaydedilmeden temizlenir.
    post_poll(member_client, options=["A\x00B", "C\x07D"])
    assert option_texts(Poll.objects.get()) == ["AB", "CD"]


def test_nul_in_question_is_rejected(member_client):
    response = post_poll(member_client, question="So\x00ru")

    assert response.status_code == 200
    assert not Poll.objects.exists()


def test_zero_width_only_options_count_as_blank(member_client):
    response = post_poll(member_client, options=["A", "\u200b", "\u200b\u2060\ufeff"])
    assert_rejected(member_client, response, "En az 2 seçenek yazmalısın.")


def test_zero_width_only_question_is_rejected(member_client):
    response = post_poll(member_client, question="\u200b\u200b")
    assert_rejected(member_client, response, "Sorunu yazmayı unutma.")


def test_bidi_override_characters_are_stripped(member_client):
    post_poll(member_client, question="\u202eSoru\u202c", options=["\u202eEvet", "Hayır\u2066"])

    poll = Poll.objects.get()
    assert poll.question == "Soru"
    assert option_texts(poll) == ["Evet", "Hayır"]


def test_duplicate_check_ignores_composed_vs_decomposed_accents(member_client):
    response = post_poll(member_client, options=["Caf\u00e9", "Cafe\u0301"])
    assert_rejected(member_client, response, "Aynı seçeneği iki kez yazdın.")


def test_zwj_emoji_sequences_are_preserved(member_client):
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
    post_poll(member_client, options=[family, "Tek başıma"])
    assert option_texts(Poll.objects.get())[0] == family


# ---------- Normalizasyon sonrası uzunluk (incelemeden) ----------


def test_question_that_grows_after_nfc_is_rejected(member_client):
    # U+0344 tek karakterdir ama NFC'de iki karaktere açılır: 200 ham karakter → 400 karakter.
    # SQLite bunu sessizce kabul eder, Postgres "value too long" ile 500 verirdi.
    response = post_poll(member_client, question="\u0344" * 200)
    assert_rejected(member_client, response, "Soru en fazla 200 karakter olabilir.")


def test_question_at_the_limit_is_still_accepted_after_normalization(member_client):
    post_poll(member_client, question="é" * 200)  # NFC'de uzamayan, tam sınırda soru
    assert len(Poll.objects.get().question) == 200
