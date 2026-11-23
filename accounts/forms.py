import time

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core import signing
from django.core.exceptions import ValidationError

from .models import User

FORM_TOKEN_SALT = "kararsizim.register-form"
# Form taze bir belirteçle geri döner, bu yüzden "yenile" demeye gerek yok: yeniden göndermek yeter.
FORM_EXPIRED_MESSAGE = "Form doğrulanamadı, lütfen bir kez daha dene."


def make_form_token(issued_at: float | None = None) -> str:
    """Kayıt formunun açıldığı anı imzalı bir belirteç yapar (bot tuzağının zaman denetimi)."""
    issued = int(time.time() if issued_at is None else issued_at)
    return signing.Signer(salt=FORM_TOKEN_SALT).sign(str(issued))


def form_token_is_valid(token: str) -> bool:
    """İmza doğru ve form, çok hızlı (bot) ya da çok eski olmayan bir zamanda gönderilmiş mi?"""
    try:
        issued = int(signing.Signer(salt=FORM_TOKEN_SALT).unsign(token or ""))
    except (signing.BadSignature, ValueError):
        return False
    age = time.time() - issued
    return settings.REGISTER_MIN_FILL_SECONDS <= age <= settings.REGISTER_MAX_AGE_SECONDS


class RegisterForm(UserCreationForm):
    """Kayıt formu: kullanıcı adı, e-posta, parola ve parola tekrarı.

    Botlara karşı harici servis yok: gizli bir tuzak alanı (insan boş bırakır, bot doldurur) ve
    imzalı bir zaman damgası. Başarısızlıkta neden söylenmez (botlara ipucu verilmez).
    """

    hp_alan = forms.CharField(
        required=False,
        label="Bu alanı boş bırak",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput)

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

        self.fields["form_ts"].initial = make_form_token()
        # Belirteç, yenilenmeden ve alan temizliğinden (veritabanı sorguları) ÖNCE denetlenir.
        # Sonradan denetlenseydi yavaş bir temizleme taze belirteci "yeterince yaşlı" yapar, eksik
        # ya da sahte belirteçli istek de tuzaktan geçerdi (MIN=0 iken hiç yakalanmazdı).
        self.token_ok = not self.is_bound or form_token_is_valid(self.data.get("form_ts", ""))
        if not self.token_ok:
            # Hata sayfası yeni bir belirteç taşısın; yoksa kullanıcı düzeltip tekrar gönderdiğinde
            # aynı eski belirteçle yine takılır.
            data = self.data.copy()
            data["form_ts"] = make_form_token()
            self.data = data

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("hp_alan") or not self.token_ok:
            raise ValidationError(FORM_EXPIRED_MESSAGE, code="form_expired")
        return cleaned_data

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
