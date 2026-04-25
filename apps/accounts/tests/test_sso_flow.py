"""End-to-end tests for the magic-link SSO flow.

Covers the happy path plus the key security invariants:
  - GET /sso/magic/ does NOT consume the token (anti-prefetch defense).
  - Cooldown blocks a second link within 60s without resetting TTL.
  - Expired / consumed tokens return 410.
  - Unsafe redirect targets are stripped.
"""

import hashlib
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import LoginToken

User = get_user_model()

pytestmark = pytest.mark.django_db


def _extract_magic_url(message_body: str) -> str:
    for line in message_body.splitlines():
        line = line.strip()
        if "/sso/magic/" in line:
            return line
    raise AssertionError("No magic link URL found in email body:\n" + message_body)


def _raw_token_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


class TestSsoLoginPage:
    def test_get_renders_login_form(self, client):
        resp = client.get(reverse("sso_login"))
        assert resp.status_code == 200
        assert b"Email" in resp.content

    def test_post_invalid_email_returns_400(self, client):
        resp = client.post(reverse("sso_login"), {"email": "not-an-email"})
        assert resp.status_code == 400


class TestMagicLinkRequest:
    def test_first_login_creates_inactive_user_and_sends_email(self, client):
        resp = client.post(
            reverse("sso_login"),
            {"email": "new@example.com", "redirect": "http://localhost:82/"},
        )
        assert resp.status_code == 200

        user = User.objects.get(email="new@example.com")
        assert user.is_active is False
        assert not user.has_usable_password()

        assert LoginToken.objects.filter(user=user).count() == 1
        token = LoginToken.objects.get(user=user)
        assert token.purpose == LoginToken.PURPOSE_ACTIVATE
        assert token.redirect_to == "http://localhost:82/"

        assert len(mail.outbox) == 1
        assert "new@example.com" in mail.outbox[0].to
        assert "/sso/magic/" in mail.outbox[0].body

    def test_existing_active_user_issues_login_token(self, client, active_user):
        resp = client.post(reverse("sso_login"), {"email": active_user.email})
        assert resp.status_code == 200

        token = LoginToken.objects.get(user=active_user)
        assert token.purpose == LoginToken.PURPOSE_LOGIN

    def test_cooldown_blocks_second_request_within_60s(self, client, active_user):
        client.post(reverse("sso_login"), {"email": active_user.email})
        assert LoginToken.objects.filter(user=active_user).count() == 1

        mail.outbox.clear()
        resp = client.post(reverse("sso_login"), {"email": active_user.email})

        assert resp.status_code == 200
        assert LoginToken.objects.filter(user=active_user).count() == 1
        assert len(mail.outbox) == 0

    def test_unsafe_redirect_is_stripped(self, client, active_user):
        client.post(
            reverse("sso_login"),
            {"email": active_user.email, "redirect": "http://evil.com/phish"},
        )
        token = LoginToken.objects.get(user=active_user)
        assert token.redirect_to == ""


class TestMagicLinkConsumption:
    def test_get_shows_confirm_page_without_consuming(self, client, active_user, make_login_token):
        link, raw = make_login_token(active_user)
        resp = client.get(reverse("sso_magic_link", args=[raw]))

        assert resp.status_code == 200
        assert b"raw_token" in resp.content or raw.encode() in resp.content
        link.refresh_from_db()
        assert link.consumed_at is None, "GET must not consume the token"

    def test_post_consumes_token_and_redirects_with_jwt(
        self, client, active_user, make_login_token
    ):
        link, raw = make_login_token(active_user, redirect_to="http://localhost:82/")
        resp = client.post(reverse("sso_magic_link", args=[raw]))

        assert resp.status_code == 302
        assert resp["Location"].startswith("http://localhost:82/")
        assert "token=" in resp["Location"]

        link.refresh_from_db()
        assert link.consumed_at is not None

    def test_post_activates_inactive_user(self, client, inactive_user, make_login_token):
        link, raw = make_login_token(inactive_user, purpose=LoginToken.PURPOSE_ACTIVATE)
        assert inactive_user.is_active is False

        client.post(reverse("sso_magic_link", args=[raw]))

        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True

    def test_expired_token_returns_410(self, client, active_user, make_login_token):
        link, raw = make_login_token(active_user)
        link.expires_at = timezone.now() - timedelta(seconds=1)
        link.save(update_fields=["expires_at"])

        resp = client.post(reverse("sso_magic_link", args=[raw]))
        assert resp.status_code == 410

    def test_already_consumed_token_returns_410(self, client, active_user, make_login_token):
        link, raw = make_login_token(active_user, consumed=True)

        resp = client.post(reverse("sso_magic_link", args=[raw]))
        assert resp.status_code == 410

    def test_unknown_token_returns_404(self, client):
        resp = client.post(reverse("sso_magic_link", args=["does-not-exist"]))
        assert resp.status_code == 404

    def test_token_hash_stored_never_matches_raw(self, active_user, make_login_token):
        """Security invariant: DB only stores sha256(raw), never raw."""
        link, raw = make_login_token(active_user)
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()
        assert link.token_hash == expected_hash
        assert link.token_hash != raw


class TestEndToEndLogin:
    def test_full_flow_from_email_to_jwt(self, client):
        """Simulate: request link → open inbox → GET confirm → POST → redirect."""
        email = "e2e@example.com"
        client.post(
            reverse("sso_login"),
            {"email": email, "redirect": "http://localhost:82/"},
        )
        assert len(mail.outbox) == 1

        magic_url = _extract_magic_url(mail.outbox[0].body)
        raw_token = _raw_token_from_url(magic_url)

        confirm = client.get(reverse("sso_magic_link", args=[raw_token]))
        assert confirm.status_code == 200

        final = client.post(reverse("sso_magic_link", args=[raw_token]))
        assert final.status_code == 302
        assert "token=" in final["Location"]

        user = User.objects.get(email=email)
        assert user.is_active is True
