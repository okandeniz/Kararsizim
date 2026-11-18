from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import User


class RegisterForm(UserCreationForm):
    """Kayıt formu: kullanıcı adı, e-posta, parola ve parola tekrarı."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
        labels = {"username": "Kullanıcı adı", "email": "E-posta"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "username"
        ].help_text = "3–20 karakter; harf, rakam ve _ kullanabilirsin. Anketlerde bu ad görünecek."
        self.fields["username"].widget.attrs.update(
            {"class": "input", "autocapitalize": "none", "spellcheck": "false"}
        )
        self.fields["email"].help_text = "E-postan kimseye gösterilmez."
        self.fields["email"].widget.attrs.update({"class": "input", "autocomplete": "email"})
        self.fields["password1"].label = "Parola"
        self.fields["password1"].widget.attrs.update({"class": "input"})
        self.fields["password2"].label = "Parola (tekrar)"
        self.fields["password2"].help_text = ""
        self.fields["password2"].widget.attrs.update({"class": "input"})

    def clean_email(self):
        # Model benzersizlik denetimi büyük/küçük harfe duyarlıdır; burada duyarsız bakılır.
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Bu e-posta ile zaten bir hesap var.", code="unique")
        return email


class EmailAuthenticationForm(AuthenticationForm):
    """E-posta + parola ile giriş. Hatalı girişte tek bir genel mesaj gösterilir."""

    error_messages = {
        "invalid_login": "E-posta veya parola hatalı.",
        "inactive": "E-posta veya parola hatalı.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        username = self.fields["username"]
        username.label = "E-posta"
        username.widget = forms.EmailInput(
            attrs={"class": "input", "autocomplete": "email", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update({"class": "input"})
