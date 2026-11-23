from django.contrib import admin

from .models import Hit


@admin.register(Hit)
class HitAdmin(admin.ModelAdmin):
    """Yalnızca inceleme: kayıtlar elle eklenip değiştirilmez (özne zaten geri çözülemeyen özet)."""

    list_display = ("scope", "short_subject", "created_at")
    # list_filter yok: guest_vote_poll:<anket> her ankete ayrı kapsam üretir, filtre şişerdi.
    search_fields = ("scope",)
    date_hierarchy = "created_at"

    @admin.display(description="özne (ilk 8)")
    def short_subject(self, obj):
        return obj.subject[:8]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
