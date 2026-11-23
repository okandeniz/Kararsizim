from django.contrib import admin
from django.urls import include, path

from abuse.decorators import protect_login

urlpatterns = [
    # Admin girişi de kaba kuvvete karşı korunur; bu yol admin.site.urls'tan ÖNCE gelmeli.
    path("admin/login/", protect_login(admin.site.login)),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("polls.urls")),
]
