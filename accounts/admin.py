from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Admin yalnızca süper kullanıcıya açıktır; e-posta burada görünebilir.
    ordering = ("-date_joined",)
    list_display = ("username", "email", "is_staff", "date_joined")
    search_fields = ("username", "email")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profil", {"fields": ("username", "first_name", "last_name")}),
        (
            "İzinler",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Önemli tarihler", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )
