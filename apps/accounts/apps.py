from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        """掛勾 SimpleJWT 的 TokenBackend.encode,RS/ES 簽章時自動帶 kid header。

        新版 simplejwt 移除 TOKEN_BACKEND_CLASS 設定,改用 monkey-patch 達到
        同樣效果 — 下游服務 (EDM / job-digger-admin 等) 用 JWKS 驗章時,
        靠 JWT header 內的 kid 對應 JWKS 內的公鑰。沒 kid 會 throw,造成
        redirect loop。
        """
        from django.conf import settings

        algorithm = settings.SIMPLE_JWT.get("ALGORITHM", "HS256")
        if not algorithm.startswith(("RS", "ES", "PS")):
            return

        import jwt as pyjwt
        from rest_framework_simplejwt.backends import TokenBackend

        from .jwt_keys import get_current_kid

        def encode_with_kid(self, payload):
            jwt_payload = payload.copy()
            if self.audience is not None:
                jwt_payload["aud"] = self.audience
            if self.issuer is not None:
                jwt_payload["iss"] = self.issuer
            return pyjwt.encode(
                jwt_payload,
                self.signing_key,
                algorithm=self.algorithm,
                headers={"kid": get_current_kid()},
            )

        TokenBackend.encode = encode_with_kid
