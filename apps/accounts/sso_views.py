"""Passwordless (magic link) SSO for Middle Platform.

Flow:
  1. User hits /sso/login/?redirect=<app_url> — enters email only.
  2. We create the user on first sight (is_active=False) or reuse an existing
     one, generate a one-time token, email a magic link, and render a
     "check your email" page.
  3. The email contains /sso/magic/<raw_token>/ — GET shows a confirmation
     page (defends against email security scanners that pre-fetch links),
     POST actually consumes the token, logs the user in, issues a JWT, and
     redirects back to the caller's app with ?token=<jwt>.
"""

import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlparse, urlunparse

from django.conf import settings
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken

from .models import LoginToken, User

_SAFE_REDIRECT_HOSTS = {
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
}


def _build_redirect_with_token(redirect_url: str, token: str) -> str:
    parsed = urlparse(redirect_url)
    extra = urlencode({"token": token})
    new_query = f"{parsed.query}&{extra}" if parsed.query else extra
    return urlunparse(parsed._replace(query=new_query))


def _edm_landing_url() -> str:
    """組出 EDM 登入完的落地 URL,讓 caller 再接 ?token=。"""
    base = settings.EDM_URL.rstrip("/")
    path = "/" + settings.EDM_LANDING_PATH.lstrip("/")
    return f"{base}{path}"


def _is_safe_redirect(redirect_url: str) -> bool:
    if not redirect_url:
        return False
    parsed = urlparse(redirect_url)
    if parsed.scheme not in {"http", "https"}:
        return False
    return (parsed.hostname or "").lower() in _SAFE_REDIRECT_HOSTS


def _issue_access_token(user) -> str:
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["display_name"] = user.display_name
    return str(refresh.access_token)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _send_magic_link(request, user: User, redirect_to: str, purpose: str) -> bool:
    """Create a LoginToken and email the magic link. Returns False if rate-limited."""
    cooldown = timezone.now() - timedelta(seconds=settings.MAGIC_LINK_RESEND_COOLDOWN_SECONDS)
    recent = LoginToken.objects.filter(user=user, created_at__gte=cooldown).exists()
    if recent:
        return False

    raw_token = secrets.token_urlsafe(32)
    LoginToken.objects.create(
        user=user,
        token_hash=_hash_token(raw_token),
        purpose=purpose,
        redirect_to=redirect_to if _is_safe_redirect(redirect_to) else "",
        expires_at=timezone.now() + timedelta(minutes=settings.MAGIC_LINK_TTL_MINUTES),
        created_ip=_client_ip(request),
    )

    base = settings.SSO_BASE_URL.rstrip("/")
    magic_url = f"{base}/sso/magic/{raw_token}/"
    subject = "Middle Platform 登入連結"
    body = (
        f"Hi {user.display_name or user.email.split('@')[0]},\n\n"
        f"點擊以下連結以登入 Middle Platform "
        f"(連結 {settings.MAGIC_LINK_TTL_MINUTES} 分鐘內有效,且只能使用一次):\n\n"
        f"{magic_url}\n\n"
        f"如果不是你本人請求,請忽略此信。\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return True


class SsoLoginView(View):
    """Request a magic link by email, or (if already logged in) show the apps page."""

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
                    "edm_url": _build_redirect_with_token(_edm_landing_url(), token),
                },
            )

        return render(
            request,
            self.template_name,
            {"redirect_url": redirect_url, "error": None},
        )

    def post(self, request):
        email = (request.POST.get("email") or "").strip().lower()
        redirect_url = request.POST.get("redirect", "")

        if not email or "@" not in email:
            return render(
                request,
                self.template_name,
                {"redirect_url": redirect_url, "error": "請輸入有效的 Email"},
                status=400,
            )

        try:
            user = User.objects.get(email=email)
            purpose = LoginToken.PURPOSE_LOGIN if user.is_active else LoginToken.PURPOSE_ACTIVATE
        except User.DoesNotExist:
            display_name = email.split("@")[0]
            user = User.objects.create_passwordless_user(email=email, display_name=display_name)
            purpose = LoginToken.PURPOSE_ACTIVATE

        sent = _send_magic_link(request, user, redirect_url, purpose)
        return render(
            request,
            "sso/magic_link_sent.html",
            {"email": email, "cooldown_hit": not sent},
        )


class SsoMagicLinkView(View):
    """Consume a magic link token.

    GET  → render a confirmation page (anti-prefetch defense).
    POST → validate token, activate+login user, issue JWT, redirect back.
    """

    def get(self, request, raw_token: str):
        link = get_object_or_404(LoginToken, token_hash=_hash_token(raw_token))
        if not link.is_usable:
            return render(
                request,
                "sso/magic_link_invalid.html",
                {
                    "reason": "此連結已過期或已被使用過,請重新請求登入連結。",
                },
                status=410,
            )
        return render(
            request,
            "sso/magic_link_confirm.html",
            {
                "raw_token": raw_token,
                "email": link.user.email,
            },
        )

    def post(self, request, raw_token: str):
        link = get_object_or_404(LoginToken, token_hash=_hash_token(raw_token))
        if not link.is_usable:
            return render(
                request,
                "sso/magic_link_invalid.html",
                {"reason": "此連結已過期或已被使用過。"},
                status=410,
            )

        link.consumed_at = timezone.now()
        link.save(update_fields=["consumed_at"])

        user = link.user
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        login(request, user)
        jwt_token = _issue_access_token(user)

        if _is_safe_redirect(link.redirect_to):
            return redirect(_build_redirect_with_token(link.redirect_to, jwt_token))

        return render(
            request,
            "sso/login_success.html",
            {
                "token": jwt_token,
                "user": user,
                "edm_url": _build_redirect_with_token(_edm_landing_url(), jwt_token),
            },
        )


class SsoLogoutView(View):
    def get(self, request):
        logout(request)
        redirect_url = request.GET.get("redirect", "")
        if _is_safe_redirect(redirect_url):
            return redirect(redirect_url)
        return redirect("sso_login")
