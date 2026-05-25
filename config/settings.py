from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    JWT_ACCESS_TOKEN_LIFETIME_MIN=(int, 30),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    JWT_ALGORITHM=(str, "HS256"),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.accounts",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise:Cloud Run 沒前面 nginx,靜態檔由 Django 自己 serve
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.accounts.middleware.SsoLoginRequiredMiddleware",
]

SSO_LOGIN_EXEMPT_PREFIXES = [
    "/sso/",
    "/api/",
    "/admin/",
    "/static/",
    "/media/",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_DATABASE"),
        "USER": env("DB_USERNAME"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="db"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise 壓縮 + manifest hash,production 一次 collectstatic 後永久 cache
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

JWT_ALGORITHM = env("JWT_ALGORITHM")
JWT_PRIVATE_KEY = env("JWT_PRIVATE_KEY", default=None)
JWT_PUBLIC_KEY = env("JWT_PUBLIC_KEY", default=None)
JWT_PRIVATE_KEY_PATH = env("JWT_PRIVATE_KEY_PATH", default=None)
JWT_PUBLIC_KEY_PATH = env("JWT_PUBLIC_KEY_PATH", default=None)

SIMPLE_JWT = {
    "ALGORITHM": JWT_ALGORITHM,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MIN")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "ISSUER": env("JWT_ISSUER", default="middle-platform"),
}

if JWT_ALGORITHM.startswith("RS"):
    from apps.accounts.jwt_keys import load_private_key_pem, load_public_key_pem

    SIMPLE_JWT["SIGNING_KEY"] = load_private_key_pem(
        base_dir=BASE_DIR,
        env_value=JWT_PRIVATE_KEY,
        env_path=JWT_PRIVATE_KEY_PATH,
    )
    SIMPLE_JWT["VERIFYING_KEY"] = load_public_key_pem(
        base_dir=BASE_DIR,
        env_value=JWT_PUBLIC_KEY,
        env_path=JWT_PUBLIC_KEY_PATH,
    )

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# --- Production / Cloud Run 反向 proxy 設定 ---
# Cloud Run 在 Google Front End 後面,Django 收到的是 HTTP,需告訴它原本是 HTTPS
# 不然 request.is_secure() 永遠 False,CSRF / cookie secure flag 會混亂
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Django 4.0+ 對跨 origin 的 POST 強制要求 CSRF_TRUSTED_ORIGINS 帶 scheme
# Cloud Run URL 通常是 https://<svc>-<hash>-<region>.run.app,先預設信任全部 run.app
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://*.run.app"],
)

EDM_URL = env("EDM_URL", default="http://localhost:82")
# 登入成功後 EDM 端要落地的路徑,預設進 SA 文件 / UML 頁
EDM_LANDING_PATH = env("EDM_LANDING_PATH", default="/sa-docs/uml")

# Job Digger Admin (Laravel 後台,共用 SSO 的另一個業務系統)
JOB_DIGGER_ADMIN_URL = env("JOB_DIGGER_ADMIN_URL", default="http://localhost:8084")
# admin 端接收 SSO token 的 callback 路徑
JOB_DIGGER_ADMIN_LANDING_PATH = env("JOB_DIGGER_ADMIN_LANDING_PATH", default="/sso/callback")

# --- Magic link (passwordless) 登入設定 ---
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="Middle Platform <noreply@middleplatform.local>",
)
SSO_BASE_URL = env("SSO_BASE_URL", default="http://localhost")
MAGIC_LINK_TTL_MINUTES = env.int("MAGIC_LINK_TTL_MINUTES", default=15)
MAGIC_LINK_RESEND_COOLDOWN_SECONDS = env.int("MAGIC_LINK_RESEND_COOLDOWN_SECONDS", default=60)
