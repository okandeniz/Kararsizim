from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView

from .forms import EmailAuthenticationForm, RegisterForm


def safe_next_url(request) -> str:
    """`next` parametresi yalnızca bu siteye ait güvenli bir adres ise döner, yoksa ''."""
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = safe_next_url(self.request)
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            # Form denetimini aynı anda geçen iki kayıt isteğinde ikincisi DB kısıtına çarpar.
            form.add_error(None, "Bu e-posta veya kullanıcı adı alınmış. Başka bir tane dene.")
            return self.form_invalid(form)
        login(self.request, user)
        messages.success(self.request, f"Hoş geldin @{user.username}!")
        return redirect(safe_next_url(self.request) or settings.LOGIN_REDIRECT_URL)


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        # LoginView'ın redirect_authenticated_user'ı `?next=/giris/` ile ValueError (500) verir.
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)
