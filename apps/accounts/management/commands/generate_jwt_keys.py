"""Generate an RSA keypair for JWT signing.

執行範例:
    python manage.py generate_jwt_keys                # 預設輸出到 BASE_DIR/keys/
    python manage.py generate_jwt_keys --out /tmp/x   # 自訂目錄
    python manage.py generate_jwt_keys --force        # 覆蓋既有金鑰

金鑰**不要 commit**。.gitignore 已加 keys/。
Production 建議用 GCP Secret Manager / env var,本地開發用檔案即可。
"""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Generate an RSA-2048 keypair for JWT (RS256) signing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            type=str,
            default=str(settings.BASE_DIR / "keys"),
            help="Output directory (default: BASE_DIR/keys/)",
        )
        parser.add_argument("--force", action="store_true", help="Overwrite existing keys")

    def handle(self, *_args, **options):
        out_dir = Path(options["out"])
        out_dir.mkdir(parents=True, exist_ok=True)

        priv_path = out_dir / "jwt_private.pem"
        pub_path = out_dir / "jwt_public.pem"

        if (priv_path.exists() or pub_path.exists()) and not options["force"]:
            raise CommandError(f"Key files already exist in {out_dir}. Use --force to overwrite.")

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        priv_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_pem = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        priv_path.write_bytes(priv_pem)
        pub_path.write_bytes(pub_pem)
        priv_path.chmod(0o600)

        self.stdout.write(self.style.SUCCESS(f"Wrote {priv_path}"))
        self.stdout.write(self.style.SUCCESS(f"Wrote {pub_path}"))
        self.stdout.write("")
        self.stdout.write("接下來:")
        self.stdout.write("  1. 在 .env 加入:")
        self.stdout.write("       JWT_ALGORITHM=RS256")
        self.stdout.write(f"       JWT_PRIVATE_KEY_PATH={priv_path}")
        self.stdout.write(f"       JWT_PUBLIC_KEY_PATH={pub_path}")
        self.stdout.write("  2. 重啟 Django,新核發的 token 即會用 RS256 簽")
        self.stdout.write("  3. 各服務透過 /.well-known/jwks.json 拉公鑰本地驗證")
