from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


def _validate_access_token(raw_token):
    """Validate a raw JWT string and return the associated user, or raise."""
    auth = JWTAuthentication()
    validated = auth.get_validated_token(raw_token)
    user = auth.get_user(validated)
    return user, validated


class VerifyTokenView(APIView):
    """Service-to-service JWT verification.

    Accepts a JWT via POST body (`{"token": "..."}`) or Authorization header.
    Returns basic user info on success, 401 on failure.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        raw_token = request.data.get("token")
        if not raw_token:
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header.lower().startswith("bearer "):
                raw_token = auth_header.split(" ", 1)[1].strip()

        if not raw_token:
            return Response(
                {"valid": False, "detail": "token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user, _ = _validate_access_token(raw_token)
        except (InvalidToken, TokenError) as exc:
            return Response(
                {"valid": False, "detail": str(exc)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "valid": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "is_staff": user.is_staff,
                    "is_active": user.is_active,
                },
            }
        )


class EdmSsoVerifyTokenView(APIView):
    """Token-exchange endpoint tailored to the EDM Vben frontend.

    Validates the SSO token and returns the shape EDM expects:
      {"code": 0, "data": {"accessToken": "...", "userInfo": {...}}}
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        raw_token = request.data.get("token") or request.data.get("hws_token")
        if not raw_token:
            return Response(
                {"code": 1, "message": "token is required", "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user, _ = _validate_access_token(raw_token)
        except (InvalidToken, TokenError) as exc:
            return Response(
                {"code": 1, "message": f"invalid token: {exc}", "data": None},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "accessToken": raw_token,
                    "userInfo": {
                        "userId": user.id,
                        "username": user.email,
                        "realName": user.display_name or user.email.split("@")[0],
                        "email": user.email,
                        "roles": ["super"] if user.is_superuser else ["user"],
                        "homePath": "/dashboard",
                        "avatar": "",
                        "desc": "SSO user from Middle Platform",
                    },
                },
            }
        )
