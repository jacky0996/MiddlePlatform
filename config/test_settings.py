"""Test-only settings.

Overrides production settings to:
  - Use in-memory SQLite (no MySQL service required in CI).
  - Use fast MD5 password hasher.
  - Capture outbound email in django.core.mail.outbox instead of sending.

This module pre-populates any env vars required by config.settings so that
tests can run without a .env file.
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DJANGO_DEBUG", "False")
os.environ.setdefault("DB_DATABASE", "test_db")
os.environ.setdefault("DB_USERNAME", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_pass")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("SSO_BASE_URL", "http://localhost")
os.environ.setdefault("EDM_URL", "http://localhost:82")

from config.settings import *  # noqa: E402, F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

MAGIC_LINK_TTL_MINUTES = 15
MAGIC_LINK_RESEND_COOLDOWN_SECONDS = 60
