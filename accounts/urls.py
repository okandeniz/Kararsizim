from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("kayit/", views.RegisterView.as_view(), name="register"),
    path("giris/", views.AppLoginView.as_view(), name="login"),
    # LogoutView yalnızca POST kabul eder (GET → 405).
    path("cikis/", LogoutView.as_view(), name="logout"),
]
