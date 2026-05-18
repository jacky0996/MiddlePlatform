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


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """Build a JWKS document from the current public key."""
    from cryptography.hazmat.primitives import serialization
    from django.conf import settings
    from jwt.utils import base64url_encode, to_base64url_uint

    pem = load_public_key_pem(
        base_dir=settings.BASE_DIR,
        env_value=getattr(settings, "JWT_PUBLIC_KEY", None),
        env_path=getattr(settings, "JWT_PUBLIC_KEY_PATH", None),
    ).encode()
    public_key = serialization.load_pem_public_key(pem)
    numbers = public_key.public_numbers()

    n = to_base64url_uint(numbers.n).decode()
    e = to_base64url_uint(numbers.e).decode()

    kid = base64url_encode(hashlib.sha256(pem).digest()).decode()[:16]

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid,
                "n": n,
                "e": e,
            }
        ]
    }
