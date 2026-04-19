"""HTML-based SSO login page for Middle Platform.

Flow:
  1. Unauthenticated visits to EDM (:82) redirect browser here with
     ?redirect=<edm_url>.
  2. On successful email/password login we mint a JWT access token and
     302 back to `redirect?token=<jwt>`, where EDM's router guard picks
     it up and exchanges it via /api/edm/sso/verify-token.
  3. A Django session cookie is also set so subsequent visits while the
     browser session is alive skip the form and immediately bounce back.
"""

from urllib.parse import urlencode, urlparse, urlunparse

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken

_SAFE_REDIRECT_HOSTS = {
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
}


def _build_redirect_with_token(redirect_url: str, token: str) -> str:
    """Append ?token=<jwt> to the caller's redirect URL, preserving query."""
    parsed = urlparse(redirect_url)
    query = parsed.query
    extra = urlencode({"token": token})
    new_query = f"{query}&{extra}" if query else extra
    return urlunparse(parsed._replace(query=new_query))


def _is_safe_redirect(redirect_url: str) -> bool:
    if not redirect_url:
        return False
    parsed = urlparse(redirect_url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in _SAFE_REDIRECT_HOSTS


def _issue_access_token(user) -> str:
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["display_name"] = user.display_name
    return str(refresh.access_token)


class SsoLoginView(View):
    template_name = "sso/login.html"

    def get(self, request):
        redirect_url = request.GET.get("redirect", "")

        if request.user.is_authenticated:
            token = _issue_access_token(request.user)
            if _is_safe_redirect(redirect_url):
                return redirect(_build_redirect_with_token(redirect_url, token))
            return render(
                request,
                "sso/login_success.html",
                {
                    "token": token,
                    "user": request.user,
                    "edm_url": _build_redirect_with_token(settings.EDM_URL, token),
                },
            )

        return render(
            request,
            self.template_name,
            {"redirect_url": redirect_url, "error": None},
        )

    def post(self, request):
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        redirect_url = request.POST.get("redirect", "")

        user = authenticate(request, username=email, password=password)
        if user is None or not user.is_active:
            return render(
                request,
                self.template_name,
                {
                    "redirect_url": redirect_url,
                    "error": "帳號或密碼錯誤",
                    "email": email,
                },
                status=401,
            )

        login(request, user)
        token = _issue_access_token(user)

        if _is_safe_redirect(redirect_url):
            return redirect(_build_redirect_with_token(redirect_url, token))

        edm_url_with_token = _build_redirect_with_token(settings.EDM_URL, token)
        return render(
            request,
            "sso/login_success.html",
            {
                "token": token,
                "user": user,
                "edm_url": edm_url_with_token,
            },
        )


class SsoLogoutView(View):
    def get(self, request):
        logout(request)
        redirect_url = request.GET.get("redirect", "")
        if _is_safe_redirect(redirect_url):
            return redirect(redirect_url)
        return redirect("sso_login")
