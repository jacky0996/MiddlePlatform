"""JWT signing-key loader and JWKS helper.

中台 JWT 演算法切換邏輯:
- 預設 HS256(向後相容 Laravel 服務目前共用 SECRET_KEY 的做法)
- 設定 JWT_ALGORITHM=RS256 後改走非對稱簽章
  - 私鑰只在中台,各服務透過 JWKS 拉公鑰本地驗證
  - 各服務不再持有 secret,中台金鑰外洩風險獨立化

讀取順序:env 內聯 PEM → env 指定路徑 → 預設路徑 BASE_DIR/keys/。
找不到金鑰時直接 raise,避免靜默退回 HS256 造成設定誤解。
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path


class JwtKeyError(RuntimeError):
    pass


def read_pem(env_value: str | None, env_path: str | None, default_path: Path) -> str:
    if env_value:
        return env_value
    path = Path(env_path) if env_path else default_path
    if not path.exists():
        raise JwtKeyError(
            f"JWT key not found. Looked for env value, then path {path}. "
            "Run `python manage.py generate_jwt_keys` to create one."
        )
    return path.read_text()


def load_private_key_pem(base_dir: Path, env_value=None, env_path=None) -> str:
    return read_pem(env_value, env_path, base_dir / "keys" / "jwt_private.pem")


def load_public_key_pem(base_dir: Path, env_value=None, env_path=None) -> str:
    return read_pem(env_value, env_path, base_dir / "keys" / "jwt_public.pem")


def _load_public_pem_bytes() -> bytes:
    from django.conf import settings

    return load_public_key_pem(
        base_dir=settings.BASE_DIR,
        env_value=getattr(settings, "JWT_PUBLIC_KEY", None),
        env_path=getattr(settings, "JWT_PUBLIC_KEY_PATH", None),
    ).encode()


@lru_cache(maxsize=1)
def get_current_kid() -> str:
    """簽 JWT 用的 kid — 跟 JWKS 公開的 kid 同一個值,確保下游能查表對應。

    取公鑰 PEM 的 sha256 前 16 字元 base64url,夠唯一且輪替金鑰時會自動換掉。
    """
    from jwt.utils import base64url_encode

    pem = _load_public_pem_bytes()
    return base64url_encode(hashlib.sha256(pem).digest()).decode()[:16]


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """Build a JWKS document from the current public key."""
    from cryptography.hazmat.primitives import serialization
    from jwt.utils import to_base64url_uint

    pem = _load_public_pem_bytes()
    public_key = serialization.load_pem_public_key(pem)
    numbers = public_key.public_numbers()

    n = to_base64url_uint(numbers.n).decode()
    e = to_base64url_uint(numbers.e).decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": get_current_kid(),
                "n": n,
                "e": e,
            }
        ]
    }
