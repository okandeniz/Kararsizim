from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower

RESERVED_USERNAMES = frozenset(
    {"admin", "kararsizim", "anket", "kayit", "giris", "cikis", "api", "static"}
)


def validate_username_not_reserved(value: str) -> None:
    if value.lower() in RESERVED_USERNAMES:
        raise ValidationError("Bu kullanıcı adı kullanılamaz.", code="reserved")


username_validators = [
    MinLengthValidator(3, message="Kullanıcı adı en az 3 karakter olmalı."),
    RegexValidator(
        r"^[A-Za-z0-9_]+$",
        message="Kullanıcı adı yalnızca harf, rakam ve _ içerebilir.",
        code="invalid_username",
    ),
    validate_username_not_reserved,
]


class UserManager(BaseUserManager):
    """E-posta ile giriş yapan kullanıcılar için yönetici."""

    use_in_migrations = True

    def get_by_natural_key(self, email):
        # Giriş sırasında e-posta büyük/küçük harf duyarsız aranır.
        return self.get(email__iexact=email.strip())

    def _create_user(self, email, username, password, **extra_fields):
        if not email:
            raise ValueError("E-posta zorunludur.")
        if not username:
            raise ValueError("Kullanıcı adı zorunludur.")
        user = self.model(email=email.strip().lower(), username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True:
            raise ValueError("Süper kullanıcının is_staff=True olması gerekir.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Süper kullanıcının is_superuser=True olması gerekir.")
        return self._create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    # E-posta giriş alanıdır ve HİÇBİR public sayfada gösterilmez.
    email = models.EmailField(
        "e-posta",
        unique=True,
        error_messages={"unique": "Bu e-posta ile zaten bir hesap var."},
    )
    # Anketlerde yalnızca kullanıcı adı görünür.
    username = models.CharField(
        "kullanıcı adı",
        max_length=20,
        unique=True,
        validators=username_validators,
        help_text="3–20 karakter; harf, rakam ve _ kullanabilirsin.",
        error_messages={"unique": "Bu kullanıcı adı alınmış."},
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        verbose_name = "kullanıcı"
        verbose_name_plural = "kullanıcılar"
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="unique_username_ci",
                violation_error_message="Bu kullanıcı adı alınmış.",
            ),
        ]

    def __str__(self):
        # E-posta asla gösterilmez: AbstractBaseUser.__str__ e-posta döndürürdü.
        return self.username

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)
