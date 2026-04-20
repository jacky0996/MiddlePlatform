from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.accounts.views import EdmSsoVerifyTokenView
from apps.accounts.sso_views import SsoLoginView, SsoLogoutView, SsoMagicLinkView


def healthcheck(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", healthcheck, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path(
        "api/edm/sso/verify-token",
        EdmSsoVerifyTokenView.as_view(),
        name="edm_sso_verify_token",
    ),
    path(
        "api/edm/sso/verify-token/",
        EdmSsoVerifyTokenView.as_view(),
    ),
    path("sso/login/", SsoLoginView.as_view(), name="sso_login"),
    path("sso/logout/", SsoLogoutView.as_view(), name="sso_logout"),
    path(
        "sso/magic/<str:raw_token>/",
        SsoMagicLinkView.as_view(),
        name="sso_magic_link",
    ),
]
