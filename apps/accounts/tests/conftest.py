import hashlib
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import LoginToken

User = get_user_model()


@pytest.fixture
def active_user(db):
    return User.objects.create_passwordless_user(
        email="alice@example.com", display_name="Alice", is_active=True
    )


@pytest.fixture
def inactive_user(db):
    return User.objects.create_passwordless_user(
        email="bob@example.com", display_name="Bob"
    )


@pytest.fixture
def make_login_token(db):
    def _make(user, *, raw_token="raw-token-xyz", minutes=15, consumed=False, purpose=LoginToken.PURPOSE_LOGIN, redirect_to=""):
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        link = LoginToken.objects.create(
            user=user,
            token_hash=token_hash,
            purpose=purpose,
            redirect_to=redirect_to,
            expires_at=timezone.now() + timedelta(minutes=minutes),
            consumed_at=timezone.now() if consumed else None,
        )
        return link, raw_token

    return _make
