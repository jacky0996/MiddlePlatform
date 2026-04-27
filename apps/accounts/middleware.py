"""Middleware that forces unauthenticated browsers to /sso/login/.

Whitelisted prefixes (e.g. /api/, /admin/, /sso/, static files) are skipped so
API clients, Django admin, and the SSO pages themselves keep working.
"""

from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect


class SsoLoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_prefixes = tuple(getattr(settings, "SSO_LOGIN_EXEMPT_PREFIXES", ()))

    def __call__(self, request):
        if request.user.is_authenticated or request.path.startswith(self.exempt_prefixes):
            return self.get_response(request)

        query = urlencode({"redirect": request.build_absolute_uri()})
        return redirect(f"/sso/login/?{query}")
