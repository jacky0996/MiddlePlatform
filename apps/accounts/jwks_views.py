from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from .jwt_keys import get_jwks


@require_GET
@cache_control(public=True, max_age=3600)
def jwks_view(_request):
    """JWKS endpoint — 各服務拉公鑰本地驗 JWT。

    Cache-Control max-age=3600:讓下游 CDN / 服務 cache 一小時。
    輪替金鑰時改 kid,下游驗章失敗會主動重抓 → 平滑切換。
    """
    return JsonResponse(get_jwks())
