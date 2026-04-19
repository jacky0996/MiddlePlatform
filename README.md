# Middle Platform

集中式身分識別與 SSO 中台服務,負責發放 JWT、驗證 token,並作為多個業務系統(EDM、未來其他站)的共用登入中樞。

## 系統定位

```
┌─ Frontend(各站前台) ────┐
│  User 登入/攜帶 Token     │
└──────────┬────────────────┘
           │
           ▼
┌─ Middle Platform(本專案)─┐
│  • 帳密儲存(Django User)  │
│  • 簽發 JWT(Access/Refresh)│
│  • Token 驗證 API          │
│  • 撤銷管理(Blacklist)    │
└──────────┬────────────────┘
           │  各站呼叫 verify-token
           ▼
┌─ 各業務系統(edm_backend …) ─┐
│  收到 JWT 後回中台驗證        │
│  拿到 user 資訊後回覆業務資料 │
└──────────────────────────────┘
```

本中台只負責**身分識別**,不持有業務資料。各業務系統擁有自己獨立的資料庫。

## 技術棧

| 分層 | 技術 |
|---|---|
| Language | Python 3.12 |
| Framework | Django 5.1 + Django REST Framework |
| Auth | djangorestframework-simplejwt(含 token blacklist) |
| Database | MySQL 8.0 |
| Container | Docker + Docker Compose |

## 專案結構

```
Middle_Platform/
├── apps/
│   └── accounts/              # 使用者與認證相關
│       ├── models.py          # User model(自訂,email 登入)
│       ├── managers.py        # UserManager(建立使用者邏輯)
│       ├── serializers.py     # 註冊/登入/Me 的 JSON 轉換
│       ├── views.py           # Register / Login / Logout / Me
│       ├── urls.py            # /api/auth/* 路由
│       └── migrations/        # Django 自動產生的 schema 變更
├── config/
│   ├── settings.py            # Django 設定(DB、JWT、CORS…)
│   ├── urls.py                # 根路由 + health check
│   ├── wsgi.py / asgi.py
│   └── __init__.py
├── docker-compose/
│   └── mysql/
│       └── init.sql           # 首次建立 DB/User 的 SQL
├── .env                       # 本地環境變數(不進 git)
├── .env.example               # 環境變數範本
├── docker-compose.yml         # 容器編排
├── Dockerfile                 # Django 映像檔
├── manage.py                  # Django 管理指令入口
├── requirements.txt
└── README.md
```

## 環境需求

- Docker 20.10+(建議 Desktop for Mac 最新版)
- Docker Compose v2+
- macOS / Linux(Windows 需用 WSL2)

> **注意**:web 服務綁定 host port 80,首次啟動需要系統授權。

## 快速啟動

### 1. 複製環境變數

```bash
cp .env.example .env
```

編輯 `.env`,確認以下值(開發預設即可):

```
DB_HOST=db
DB_PORT=3306
DB_DATABASE=platform_db
DB_USERNAME=developer
DB_PASSWORD='dqzrYAEsFZz78wGJ6eU8'
MYSQL_ROOT_PASSWORD=root_password
```

### 2. 產生 migration 檔(**首次啟動必要**)

```bash
docker compose run --rm web python manage.py makemigrations accounts
```

這一步會產生 `apps/accounts/migrations/0001_initial.py`,**記得 commit 進 git**。

### 3. 啟動全部服務

```bash
docker compose up -d
```

首次啟動會:
- 建立 `middle_platform_db` 容器,執行 `init.sql` 建立 `platform_db` + `developer` 帳號
- 建立 `middle_platform_web` 容器,自動執行 `python manage.py migrate`(見 `docker-compose.yml` 的 `command`)

### 4. 驗證服務

```bash
curl http://localhost/api/health/
# {"status": "ok"}
```

## 服務端點

| 方法 | 路徑 | 用途 | 認證 |
|---|---|---|---|
| GET | `/api/health/` | 健康檢查 | 不需要 |
| POST | `/api/auth/register/` | 註冊 | 不需要 |
| POST | `/api/auth/login/` | 登入(取得 JWT) | 不需要 |
| POST | `/api/auth/refresh/` | 用 refresh token 換新 access token | 不需要 |
| POST | `/api/auth/logout/` | 登出(將 refresh token 列入黑名單) | 需要 |
| GET | `/api/auth/me/` | 取得目前使用者資訊 | 需要 |
| GET | `/admin/` | Django Admin 管理後台 | 需要 superuser |

### 範例:註冊 → 登入 → 查詢自己

```bash
# 註冊
curl -X POST http://localhost/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SafePass!234", "display_name": "Test"}'

# 登入(取 token)
curl -X POST http://localhost/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SafePass!234"}'
# → { "access": "...", "refresh": "..." }

# 帶 token 查詢自己
curl http://localhost/api/auth/me/ \
  -H "Authorization: Bearer <access_token>"
```

### 建立 superuser(進 Django Admin 用)

```bash
docker compose exec web python manage.py createsuperuser
```

## Port 規劃

| 服務 | Host Port | 容器內 Port | 說明 |
|---|---|---|---|
| Middle Platform web | **80** | 8000 | Django 開發伺服器 |
| Middle Platform db  | **3306** | 3306 | MySQL(管理工具可連) |

若本機其他服務佔用 80(如 edm_backend 用 81),請用 `DJANGO_PORT` 環境變數覆寫:

```bash
DJANGO_PORT=8080 docker compose up -d
```

## 常用操作

```bash
# 重啟
docker compose restart web

# 看 log
docker compose logs -f web

# 進容器 shell
docker compose exec web bash

# 跑 Django 指令
docker compose exec web python manage.py shell
docker compose exec web python manage.py createsuperuser

# 新增 model 欄位後產 migration
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# 停止(保留資料)
docker compose down

# 完全清除(含 MySQL 資料,init.sql 會重新執行)
docker compose down -v
```

## 環境變數

| 變數 | 用途 | 範例 |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django SECRET_KEY(production 必改) | `change-me-long-random-string` |
| `DJANGO_DEBUG` | Debug mode | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | 允許的 host 列表 | `localhost,127.0.0.1` |
| `DJANGO_PORT` | web 服務對外 port | `80` |
| `CORS_ALLOWED_ORIGINS` | 允許跨域來源 | `http://localhost:3000` |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密碼(容器啟動用) | `root_password` |
| `DB_CONNECTION` | DB 驅動 | `mysql` |
| `DB_HOST` | DB 主機(容器內為 `db`) | `db` |
| `DB_PORT` | DB port | `3306` |
| `DB_DATABASE` | DB 名稱 | `platform_db` |
| `DB_USERNAME` | DB 使用者 | `developer` |
| `DB_PASSWORD` | DB 密碼 | `dqzrYAEsFZz78wGJ6eU8` |
| `JWT_ACCESS_TOKEN_LIFETIME_MIN` | Access token 存活分鐘數 | `30` |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Refresh token 存活天數 | `7` |

## 資料庫設計

目前 `platform_db` 內的主要資料表:

| 表 | 來源 | 用途 |
|---|---|---|
| `accounts_user` | 本專案自訂 | 使用者帳密、profile |
| `auth_group` / `auth_permission` / ... | Django 內建 | 權限與群組 |
| `django_session` | Django 內建 | Session 儲存 |
| `django_admin_log` | Django Admin | Admin 操作紀錄 |
| `token_blacklist_outstandingtoken` | SimpleJWT | 已發出的 refresh token |
| `token_blacklist_blacklistedtoken` | SimpleJWT | 已撤銷(登出)的 refresh token |
| `django_migrations` | Django 內建 | 記錄已執行的 migration |

只有 `accounts_user` 是業務邏輯表,其餘為框架基礎設施。

## 與其他服務整合

本中台會擔任所有業務系統的身分驗證中樞。外部系統(如 edm_backend)的整合方式:

1. 使用者帶著中台簽發的 JWT 呼叫業務系統
2. 業務系統收到後 POST 回中台 verify-token endpoint(**待實作**)
3. 中台回覆 user 資訊,業務系統據此回傳業務資料

verify-token endpoint 的詳細規格將於後續版本提供。

### 本地開發 Docker 網路注意事項

若其他服務(如 edm_backend)在 docker 容器內要呼叫本中台:
- **不要用** `http://localhost` —— 容器內的 localhost 指向容器本身
- **應該用** `http://host.docker.internal`(需在該容器的 compose 加上 `extra_hosts: ["host.docker.internal:host-gateway"]`)

## 開發筆記

### Django 的 migration 工作流

1. 改 `models.py`
2. `docker compose exec web python manage.py makemigrations` — 產生 migration 檔(**進 git**)
3. `docker compose exec web python manage.py migrate` — 套用到 DB

容器啟動時 `docker-compose.yml` 的 `command` 已包含 `migrate`,拉下新 code 後 restart 即可自動更新 schema。

### 為什麼 `migrations/` 剛 clone 下來可能是空的

Django 不預載 migration 檔案 —— 每個專案第一次建立自訂 model 時都要跑一次 `makemigrations`。產出的檔案要 commit 進 git,之後其他開發者或部署環境就不需要重跑 makemigrations,只要 `migrate` 即可。

## License

Private / Portfolio use.
