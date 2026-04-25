"""Tests for SsoLoginRequiredMiddleware.

Uses RequestFactory to test the middleware directly, independent of any
specific URL conf. The production URLs all fall under whitelisted prefixes,
so we simulate a non-whitelisted path ("/app/") to verify the redirect path.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.accounts.middleware import SsoLoginRequiredMiddleware


@pytest.fixture
def factory():
    return RequestFactory()


@pytest.fixture
def sentinel_response():
    class _Resp:
        status_code = 200

    def _get_response(_request):
        return _Resp()

    return _get_response


class TestSsoLoginRequiredMiddleware:
    def test_anonymous_on_protected_path_is_redirected_to_sso_login(
        self, factory, sentinel_response
    ):
        mw = SsoLoginRequiredMiddleware(sentinel_response)
        request = factory.get("/app/dashboard/")
        request.user = AnonymousUser()

        resp = mw(request)

        assert resp.status_code == 302
        assert resp["Location"].startswith("/sso/login/")
        assert "redirect=" in resp["Location"]

    def test_api_prefix_is_whitelisted(self, factory, sentinel_response):
        mw = SsoLoginRequiredMiddleware(sentinel_response)
        request = factory.get("/api/health/")
        request.user = AnonymousUser()

        resp = mw(request)
        assert resp.status_code == 200

    def test_sso_prefix_is_whitelisted(self, factory, sentinel_response):
        mw = SsoLoginRequiredMiddleware(sentinel_response)
        request = factory.get("/sso/login/")
        request.user = AnonymousUser()

        resp = mw(request)
        assert resp.status_code == 200

    def test_admin_prefix_is_whitelisted(self, factory, sentinel_response):
        mw = SsoLoginRequiredMiddleware(sentinel_response)
        request = factory.get("/admin/")
        request.user = AnonymousUser()

        resp = mw(request)
        assert resp.status_code == 200

    def test_authenticated_user_passes_through(self, factory, sentinel_response, active_user):
        mw = SsoLoginRequiredMiddleware(sentinel_response)
        request = factory.get("/app/dashboard/")
        request.user = active_user

        resp = mw(request)
        assert resp.status_code == 200
