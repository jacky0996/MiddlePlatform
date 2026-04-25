from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


class TestLoginTokenState:
    def test_fresh_token_is_usable(self, active_user, make_login_token):
        link, _ = make_login_token(active_user, minutes=15)
        assert link.is_usable
        assert not link.is_consumed
        assert not link.is_expired

    def test_consumed_token_is_not_usable(self, active_user, make_login_token):
        link, _ = make_login_token(active_user, consumed=True)
        assert link.is_consumed
        assert not link.is_usable

    def test_expired_token_is_not_usable(self, active_user, make_login_token):
        link, _ = make_login_token(active_user)
        link.expires_at = timezone.now() - timedelta(seconds=1)
        link.save(update_fields=["expires_at"])
        assert link.is_expired
        assert not link.is_usable

    def test_both_expired_and_consumed_still_not_usable(self, active_user, make_login_token):
        link, _ = make_login_token(active_user, consumed=True)
        link.expires_at = timezone.now() - timedelta(seconds=1)
        link.save(update_fields=["expires_at"])
        assert not link.is_usable


class TestUserManager:
    def test_create_passwordless_user_has_unusable_password(self, db):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_passwordless_user(email="new@example.com")
        assert not user.has_usable_password()
        assert user.is_active is False

    def test_create_user_normalizes_email(self, db):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(email="Mixed@Example.COM", password="x")
        assert user.email == "Mixed@example.com"

    def test_create_user_requires_email(self, db):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="x")
