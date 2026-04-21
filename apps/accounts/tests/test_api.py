"""API-layer tests: health, /api/auth/me, verify-token, EDM token exchange."""

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


def _access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class TestHealth:
    def test_health_endpoint_is_public(self, client):
        resp = client.get("/api/health/")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestMeEndpoint:
    def test_unauthenticated_is_rejected(self, client):
        resp = client.get(reverse("me"))
        assert resp.status_code == 401

    def test_authenticated_returns_profile(self, client, active_user):
        token = _access_token_for(active_user)
        resp = client.get(
            reverse("me"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == active_user.email


class TestVerifyTokenEndpoint:
    def test_valid_token_returns_user_info(self, client, active_user):
        token = _access_token_for(active_user)
        resp = client.post(
            reverse("verify_token"),
            data={"token": token},
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["user"]["email"] == active_user.email

    def test_invalid_token_returns_401(self, client):
        resp = client.post(
            reverse("verify_token"),
            data={"token": "garbage.jwt.value"},
            content_type="application/json",
        )
        assert resp.status_code == 401
        assert resp.json()["valid"] is False

    def test_missing_token_returns_400(self, client):
        resp = client.post(
            reverse("verify_token"), data={}, content_type="application/json"
        )
        assert resp.status_code == 400


class TestEdmSsoVerifyToken:
    url = "/api/edm/sso/verify-token"

    def test_valid_token_returns_vben_shape(self, client, active_user):
        token = _access_token_for(active_user)
        resp = client.post(
            self.url, data={"token": token}, content_type="application/json"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["accessToken"] == token
        assert body["data"]["userInfo"]["email"] == active_user.email
        assert body["data"]["userInfo"]["roles"] == ["user"]

    def test_superuser_role_is_super(self, client, active_user):
        active_user.is_superuser = True
        active_user.save(update_fields=["is_superuser"])
        token = _access_token_for(active_user)

        resp = client.post(
            self.url, data={"token": token}, content_type="application/json"
        )
        assert resp.json()["data"]["userInfo"]["roles"] == ["super"]

    def test_invalid_token_returns_code_1(self, client):
        resp = client.post(
            self.url, data={"token": "garbage"}, content_type="application/json"
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 1

    def test_hws_token_alias_is_accepted(self, client, active_user):
        token = _access_token_for(active_user)
        resp = client.post(
            self.url, data={"hws_token": token}, content_type="application/json"
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
