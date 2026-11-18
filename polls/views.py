from django.shortcuts import render


def feed(request):
    # Geçici akış sayfası. Gerçek akış Faz 4'te gelecek.
    return render(request, "polls/feed.html")
