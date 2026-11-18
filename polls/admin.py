from django.contrib import admin
from django.db.models import Count

from .models import MAX_OPTIONS, MIN_OPTIONS, Option, Poll, Vote


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    min_num = MIN_OPTIONS
    max_num = MAX_OPTIONS
    ordering = ("position",)


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "author", "vote_count", "created_at")
    list_select_related = ("author",)
    search_fields = ("question", "author__username")
    raw_id_fields = ("author",)
    date_hierarchy = "created_at"
    inlines = [OptionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_vote_count=Count("votes"))

    @admin.display(description="oy sayısı", ordering="_vote_count")
    def vote_count(self, obj):
        return obj._vote_count


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    # Moderasyon için: oyları görüp silebilmek. Üye gösteriminde yalnızca kullanıcı adı çıkar.
    list_display = ("poll", "option", "user", "created_at")
    list_select_related = ("poll", "option", "user")
    raw_id_fields = ("poll", "option", "user")
    date_hierarchy = "created_at"
