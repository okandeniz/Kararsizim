from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.forms import BaseInlineFormSet

from .models import MAX_OPTIONS, MIN_OPTIONS, Option, Poll, Vote


class OptionInlineFormSet(BaseInlineFormSet):
    """Admin'de de anket kuralı geçerli olsun: silinmeyen seçenek sayısı MIN–MAX arasında olmalı.

    `min_num`/`max_num` yalnızca form sayısını belirler, doğrulamayı garanti etmez.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        count = sum(
            1
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        )
        if not MIN_OPTIONS <= count <= MAX_OPTIONS:
            raise ValidationError(
                f"Bir anketin {MIN_OPTIONS} ile {MAX_OPTIONS} arası seçeneği olmalı."
            )


class OptionInline(admin.TabularInline):
    model = Option
    formset = OptionInlineFormSet
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
