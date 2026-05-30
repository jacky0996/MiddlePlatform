"""客製 SimpleJWT TokenBackend — 簽 RS/ES 演算法 JWT 時自動帶 kid header。

下游服務(EDM / job-digger-admin / job-digger)用 JWKS 驗章時,Firebase JWT
透過 kid 對應 JWKS 內的公鑰;沒 kid 會 throw `kid empty`。中台這裡簽的時候
把 kid 塞進 header,下游驗章就會自動命中對應的 key。

對稱演算法(HS256)沒有 kid 概念,維持原樣不動。
"""

from __future__ import annotations

import jwt
from rest_framework_simplejwt.backends import TokenBackend


class KidAwareTokenBackend(TokenBackend):
    """RS/ES 簽章時自動把 kid 塞進 JWT header。"""

    def encode(self, payload):
        jwt_payload = payload.copy()
        if self.audience is not None:
            jwt_payload["aud"] = self.audience
        if self.issuer is not None:
            jwt_payload["iss"] = self.issuer

        headers = None
        if self.algorithm.startswith(("RS", "ES", "PS")):
            from .jwt_keys import get_current_kid

            headers = {"kid": get_current_kid()}

        token = jwt.encode(
            jwt_payload,
            self.signing_key,
            algorithm=self.algorithm,
            headers=headers,
        )
        return token
