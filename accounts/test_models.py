import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

User = get_user_model()

pytestmark = pytest.mark.django_db


def make_user(email="ali@example.com", username="ali", password="Guclu-Parola-123"):
    return User.objects.create_user(email=email, username=username, password=password)


def test_create_user():
    user = make_user()
    assert user.pk is not None
    assert user.check_password("Guclu-Parola-123")
    assert not user.is_staff
    assert not user.is_superuser


def test_email_is_lowercased_on_create():
    user = make_user(email="Ali@Example.COM")
    assert user.email == "ali@example.com"


def test_email_is_lowercased_on_save():
    user = make_user()
    user.email = "  YENI@Example.com "
    user.save()
    user.refresh_from_db()
    assert user.email == "yeni@example.com"


def test_str_returns_username_not_email():
    user = make_user()
    assert str(user) == "ali"
    assert user.email not in str(user)


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", username="ali", password="x")


def test_create_superuser_flags():
    admin_user = User.objects.create_superuser(
        email="boss@example.com", username="patron", password="Guclu-Parola-123"
    )
    assert admin_user.is_staff
    assert admin_user.is_superuser


def test_login_field_is_email_and_case_insensitive():
    make_user(email="ali@example.com")
    assert authenticate(username="ALI@example.com", password="Guclu-Parola-123") is not None
    assert authenticate(username="ali@example.com", password="yanlis") is None


@pytest.mark.parametrize(
    "username",
    ["ab", "a" * 21, "ali veli", "ali-veli", "ali.veli", "ali@", "çağrı", "admin", "Admin", "API"],
)
def test_invalid_usernames_are_rejected(username):
    user = User(email="x@example.com", username=username)
    with pytest.raises(ValidationError) as exc_info:
        user.full_clean(exclude=["password"])
    assert "username" in exc_info.value.message_dict


@pytest.mark.parametrize("username", ["abc", "Ali_123", "a" * 20, "_x_"])
def test_valid_usernames_are_accepted(username):
    user = User(email="x@example.com", username=username)
    user.full_clean(exclude=["password"])


def test_username_uniqueness_is_case_insensitive_in_validation():
    make_user(email="a@example.com", username="Ali")
    other = User(email="b@example.com", username="ali")
    with pytest.raises(ValidationError) as exc_info:
        other.full_clean(exclude=["password"], validate_constraints=True)
    assert "Bu kullanıcı adı alınmış." in str(exc_info.value)


def test_username_uniqueness_is_case_insensitive_in_database():
    make_user(email="a@example.com", username="Ali")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(email="b@example.com", username="ALI", password="x")


def test_email_must_be_unique_regardless_of_case():
    make_user(email="a@example.com", username="ali")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(email="A@Example.com", username="veli", password="x")
