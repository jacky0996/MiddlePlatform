# Middle Platform

集中式身分識別與 SSO 中台服務。負責**簽發 JWT**、**驗證 token**,作為多個業務系統(EDM、未來其他站)的共用登入中樞。

- 認證採 **Passwordless Magic Link**(Email 寄送一次性連結),不儲存密碼。
- 對外業務系統提供 `/api/edm/sso/verify-token` 做 token 交換。
- 全站預設受保護,未登入流量一律導至 `/sso/login/`。

> 這是我用來面試 SA / 工程師職位的作品集專案,重點在**展現架構決策與安全設計**,不以高吞吐量為優化目標。完整設計脈絡請見 [`docs/`](./docs)。

---

## 文件索引

| 文件 | 對象 | 內容 |
|---|---|---|
| [docs/user-guide.md](./docs/user-guide.md) | 使用者 | SSO 登入操作手冊(不含技術細節) |
| [docs/use-cases.md](./docs/use-cases.md) | 開發者 / SA | Use Case Diagram 與逐條 Use Case 規格 |
| [docs/architecture.md](./docs/architecture.md) | 開發者 / SA | C4 Context / Container / 內部模組 + Class / State Diagram |
| [docs/user-flow.md](./docs/user-flow.md) | 開發者 / SA | 使用者流程圖 + SSO 登入 Sequence Diagram |
| [docs/adr/](./docs/adr/) | 開發者 | 關鍵技術決策紀錄(Roadmap) |

---

## 技術棧

| 分層 | 技術 |
|---|---|
| Language | Python 3.12 |
| Framework | Django 5.1 + Django REST Framework |
| Auth | djangorestframework-simplejwt(含 token blacklist)+ 自製 Magic Link |
| Database | MySQL 8.0 |
| Container | Docker + Docker Compose |
| Email(dev) | Django console backend(印到 `docker compose logs`) |

---

## 系統定位(簡略)

```
[User] ──Email──► [Middle Platform]
                        │ 簽 JWT
                        ▼
               [EDM / 其他業務系統]
                        │ 帶 JWT 回中台驗證
                        └────────────► [Middle Platform /api/.../verify-token]
```

完整架構圖請見 [docs/architecture.md](./docs/architecture.md)。

---

## 專案結構

```
Middle_Platform/
├── apps/
│   └── accounts/                 # 使用者與認證
│       ├── models.py             # User, LoginToken(只存 sha256 hash)
│       ├── managers.py           # create_user / create_passwordless_user
│       ├── serializers.py        # DRF I/O 格式
│       ├── views.py              # Register / Login / Me / VerifyToken / EdmSsoVerifyToken
│       ├── sso_views.py          # SsoLogin / SsoMagicLink / SsoLogout(HTML 流程)
│       ├── middleware.py         # SsoLoginRequiredMiddleware(未登入導走)
│       ├── admin.py              # Django Admin 註冊
│       ├── urls.py               # /api/auth/* 路由
│       ├── templates/sso/        # 登入相關所有頁面
│       └── migrations/
├── config/
│   ├── settings.py               # Django 設定 + JWT + Email + Magic Link
│   ├── urls.py                   # 根路由(/admin, /api, /sso)
│   ├── wsgi.py / asgi.py
│   └── __init__.py
├── docs/                         # SA 文件:架構、流程、ADR
├── docker-compose/mysql/init.sql
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── requirements.txt
└── README.md
```

---

## 快速啟動

### 1. 複製環境變數

```bash
cp .env.example .env
```

關鍵設定(開發預設即可):

```
DJANGO_SECRET_KEY=change-me
DB_HOST=db
DB_DATABASE=platform_db
DB_USERNAME=developer
DB_PASSWORD=dqzrYAEsFZz78wGJ6eU8
MYSQL_ROOT_PASSWORD=root_password

# Magic Link
EDM_URL=http://localhost:82
SSO_BASE_URL=http://localhost
MAGIC_LINK_TTL_MINUTES=15
MAGIC_LINK_RESEND_COOLDOWN_SECONDS=60
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=Middle Platform <noreply@middleplatform.local>
```

### 2. 啟動

```bash
docker compose up -d
```

首次啟動會:
- 建立 MySQL 容器並執行 `init.sql`
- 建立 web 容器並自動 `python manage.py migrate`

### 3. 建立管理員帳號(選用)

```bash
docker compose exec web python manage.py createsuperuser
```

### 4. 驗證服務

```bash
curl http://localhost/api/health/
# {"status": "ok"}
```

打開瀏覽器進入 `http://localhost/sso/login/`,輸入任意 Email → 登入連結會印在 `docker compose logs -f web` 裡。

---

## 服務端點

### SSO HTML 流程(給瀏覽器)

| 方法 | 路徑 | 用途 |
|---|---|---|
| GET | `/sso/login/` | 登入頁(輸入 Email) |
| POST | `/sso/login/` | 寄送 Magic Link |
| GET | `/sso/magic/<token>/` | 顯示「確認登入」頁(防 Email 掃描器預抓) |
| POST | `/sso/magic/<token>/` | 真正消耗 token、簽 JWT、導回業務系統 |
| GET | `/sso/logout/` | 登出 |

### API(給程式 / 業務系統)

| 方法 | 路徑 | 用途 | 認證 |
|---|---|---|---|
| GET | `/api/health/` | 健康檢查 | 公開 |
| POST | `/api/auth/register/` | 程式化註冊(含密碼) | 公開 |
| POST | `/api/auth/login/` | 帳密登入取得 JWT | 公開 |
| POST | `/api/auth/refresh/` | 用 refresh 換新 access | 公開 |
| POST | `/api/auth/logout/` | refresh token 加入黑名單 | 需 JWT |
| GET | `/api/auth/me/` | 目前使用者資訊 | 需 JWT |
| POST | `/api/auth/verify-token/` | 通用 token 驗證 | 公開 |
| POST | `/api/edm/sso/verify-token` | EDM 專用 token 交換(Vben 格式) | 公開 |
| GET | `/admin/` | Django Admin | 需 superuser |

### 範例:EDM 收到 SSO token 後驗證

```bash
curl -X POST http://localhost/api/edm/sso/verify-token \
  -H "Content-Type: application/json" \
  -d '{"token": "<JWT_FROM_SSO_REDIRECT>"}'

# → {"code":0,"data":{"accessToken":"...","userInfo":{...}}}
```

---

## 全站鎖定設計(Middleware)

`apps.accounts.middleware.SsoLoginRequiredMiddleware` 在每個請求進入 view 前檢查 `request.user`,**未登入一律 302 導到 `/sso/login/?redirect=<原 URL>`**。

白名單(`SSO_LOGIN_EXEMPT_PREFIXES`):
- `/sso/` — 登入頁本身
- `/api/` — DRF API 用 JWT 自己認證
- `/admin/` — Django Admin 有自己的登入頁
- `/static/`, `/media/` — 靜態檔

這樣即使未來新增任何 view,都預設是受保護的 —— 安全預設 (secure by default)。

---

## 資料庫設計

| 表 | 來源 | 用途 |
|---|---|---|
| `accounts_user` | 本專案 | 使用者主表 (email, display_name, is_active, is_staff) |
| `accounts_login_token` | 本專案 | Magic Link token 的 **hash**(sha256)、purpose、TTL、消耗時間、來源 IP |
| `auth_*` / `django_*` | Django 內建 | 權限、session、admin log、migration 紀錄 |
| `token_blacklist_*` | SimpleJWT | 已發出 / 已撤銷的 refresh token |

**安全要點**:`accounts_login_token` 永遠不儲存原始 token,只儲存 sha256 hash。原始 token 只在寄出的 Email 裡存在一次,即使 DB 外洩也無法被用來登入。

---

## 環境變數

| 變數 | 用途 | 預設 |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django SECRET_KEY | — |
| `DJANGO_DEBUG` | Debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | 允許 host | `localhost,127.0.0.1` |
| `DJANGO_PORT` | web 對外 port | `80` |
| `CORS_ALLOWED_ORIGINS` | 允許跨域來源 | `[]` |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密碼 | — |
| `DB_HOST` / `DB_PORT` / `DB_DATABASE` / `DB_USERNAME` / `DB_PASSWORD` | 資料庫連線 | — |
| `JWT_ACCESS_TOKEN_LIFETIME_MIN` | Access token 存活 | `30` |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Refresh token 存活 | `7` |
| `EDM_URL` | EDM 前台 URL(登入成功按鈕) | `http://localhost:82` |
| `SSO_BASE_URL` | Magic Link 組信時使用的 base URL | `http://localhost` |
| `MAGIC_LINK_TTL_MINUTES` | Magic Link 有效時間 | `15` |
| `MAGIC_LINK_RESEND_COOLDOWN_SECONDS` | 重寄冷卻 | `60` |
| `EMAIL_BACKEND` | Django email 後端 | console |
| `DEFAULT_FROM_EMAIL` | 寄件者 | `Middle Platform <noreply@middleplatform.local>` |

---

## 常用操作

```bash
# 啟動 / 停止
docker compose up -d
docker compose down

# 完全清除(含 MySQL volume)
docker compose down -v

# Log
docker compose logs -f web

# 進容器
docker compose exec web bash
docker compose exec web python manage.py shell

# 建立管理員
docker compose exec web python manage.py createsuperuser

# Migration
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

---

## 已知限制與 Roadmap

| 項目 | 現況 | 下一步 |
|---|---|---|
| Email 發送 | Console backend(印 log) | 加 Mailpit container 做 Demo,Prod 接 SES / SendGrid |
| Rate limiting | 僅有 60 秒重寄 cooldown | 加入 per-IP 限流(django-ratelimit / nginx) |
| ADR 文件 | 待撰寫 | 補齊:Passwordless、JWT vs Session、Token Hash Only |
| Observability | 僅 Django log | 加入結構化 log + Prometheus metrics |
| CI/CD | 無 | GitHub Actions:lint + test + docker build |
| 測試 | 無 | pytest + pytest-django,至少覆蓋 magic link 流程 |

---

## License

Private / Portfolio use.
