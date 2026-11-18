from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PollForm
from .models import Poll


def feed(request):
    # Geçici akış sayfası. Gerçek akış Faz 4'te gelecek.
    return render(request, "polls/feed.html")


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
    # Oylama Faz 4'te gelecek; şimdilik soru, yazar, zaman ve seçenekler gösterilir.
    poll = get_object_or_404(
        Poll.objects.select_related("author").prefetch_related("options"), pk=pk
    )
    return render(request, "polls/detail.html", {"poll": poll})
