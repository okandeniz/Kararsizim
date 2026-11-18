import uuid
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.views import safe_next_url

from .forms import PollForm
from .models import Option, Poll, Vote
from .voting import attach_results, read_voter_token, set_voter_cookie, voter_filter

POLLS_PER_PAGE = 20

MSG_ALREADY_VOTED = "Bu ankete zaten oy verdin."
MSG_INVALID_OPTION = "Geçersiz seçenek."
MSG_VOTE_SAVED = "Oyun kaydedildi, teşekkürler!"


def feed(request):
    paginator = Paginator(Poll.objects.select_related("author"), POLLS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    polls = attach_results(page.object_list, voter_filter(request))
    context = {"polls": polls, "page_obj": page, "next": request.get_full_path()}
    return render(request, "polls/feed.html", context)


def login_required_with_message(message):
    """login_required gibi çalışır; ek olarak giriş sayfasında gösterilecek bir mesaj bırakır."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.info(request, message)
                return redirect_to_login(request.get_full_path())
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


@login_required_with_message("Anket oluşturmak için giriş yapmalısın.")
def create(request):
    if request.method == "POST":
        form = PollForm(request.POST)
        if form.is_valid():
            poll = form.save(author=request.user)
            messages.success(request, "Anketin yayında! 🎉")
            return redirect("polls:detail", pk=poll.pk)
    else:
        form = PollForm()
    return render(request, "polls/create.html", {"form": form})


def detail(request, pk):
    poll = get_object_or_404(Poll.objects.select_related("author"), pk=pk)
    (poll,) = attach_results([poll], voter_filter(request))
    context = {"poll": poll, "next": request.path, "is_detail": True}
    return render(request, "polls/detail.html", context)


def is_fetch_request(request) -> bool:
    return request.headers.get("X-Requested-With") == "fetch"


def vote_error(request, poll, message, status):
    """Geçersiz istek (400) ve fetch hataları kısa düz metin döner; normal formda "zaten oy
    verdin" gibi durumlar mesaj + yönlendirmeyle gösterilir."""
    if is_fetch_request(request) or status == 400:
        return HttpResponse(message, status=status, content_type="text/plain; charset=utf-8")
    messages.info(request, message)
    return redirect(safe_next_url(request) or reverse("polls:detail", kwargs={"pk": poll.pk}))


@require_POST
def vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)

    # Seçenek gerçekten bu ankete ait mi? (Başka anketin seçeneği veya uydurma id → 400.)
    try:
        option = Option.objects.filter(pk=int(request.POST.get("option", "")), poll=poll).first()
    except (TypeError, ValueError, OverflowError):
        option = None
    if option is None:
        return vote_error(request, poll, MSG_INVALID_OPTION, status=400)

    # Oy sahibi: üye → user; anonim → imzalı çerezdeki UUID (yoksa yenisi üretilir).
    new_token = None
    if request.user.is_authenticated:
        voter = {"user": request.user}
    else:
        token = read_voter_token(request)
        if token is None:
            token = new_token = uuid.uuid4()
        voter = {"voter_token": token}

    try:
        with transaction.atomic():
            Vote.objects.create(poll=poll, option=option, **voter)
    except IntegrityError:
        # Yalnızca gerçekten oy varsa "zaten oy verdin" de. Başka bir ihlal (ör. anket veya
        # seçenek aynı anda silindi) yanlış mesajla gizlenmesin.
        if Vote.objects.filter(poll=poll, **voter).exists():
            return vote_error(request, poll, MSG_ALREADY_VOTED, status=409)
        return vote_error(request, poll, MSG_INVALID_OPTION, status=400)

    if is_fetch_request(request):
        (poll,) = attach_results([poll], voter)
        response = render(request, "polls/_poll_results.html", {"poll": poll})
    else:
        messages.success(request, MSG_VOTE_SAVED)
        response = redirect(
            safe_next_url(request) or reverse("polls:detail", kwargs={"pk": poll.pk})
        )

    if new_token is not None:
        set_voter_cookie(response, new_token)
    return response
