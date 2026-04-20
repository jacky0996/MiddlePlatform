from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.email


class LoginToken(models.Model):
    """One-time magic link token for passwordless login / activation.

    We never store the raw token — only its sha256 hash. The raw token lives
    only in the URL sent to the user's email.
    """

    PURPOSE_ACTIVATE = "activate"
    PURPOSE_LOGIN = "login"
    PURPOSE_CHOICES = [
        (PURPOSE_ACTIVATE, "Activate account"),
        (PURPOSE_LOGIN, "Login"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES)
    redirect_to = models.CharField(max_length=512, blank=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_login_token"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.email} / {self.purpose} / {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return not self.is_consumed and not self.is_expired
