# hemu_oversea_fastapi

English | [简体中文](./README.zh.md)

FastAPI backend for HeMu Oversea. Includes environment loading, PostgreSQL, layered layout, settings, unified responses/errors, JWT auth, RBAC, CORS, and Request ID.

HTTP entry points are split by client (**App**, **admin**, **common**); `services/` and `models/` remain shared. JWTs carry `aud` (`app` / `admin`) so tokens are not interchangeable. Refresh tokens are persisted and revocable; failed logins are rate-limited.

Common headers (`X-Sign` / `X-Timestamp` / `X-Channel`) are parsed and logged today; they are not validated yet. A dedicated pytest database is not wired up yet.

## Stack

- Python 3.13+, uv, Uvicorn
- FastAPI + Pydantic v2 + pydantic-settings
- PostgreSQL 16 (Docker Compose) + SQLAlchemy 2.0 + Alembic + psycopg v3
- JWT (access + refresh, with `aud`) + Argon2 password hashing
- Roles: `admin` / `operator` / `user`

## Layout

```text
app/
  main.py                 # Lifespan, middleware, routers
  api/                    # HTTP (split by client)
    router.py             # app / admin / common under /api/v1
    health.py             # GET /health
    app/                  # App auth & /users/me
    admin/                # Admin auth, ping, users (no public register)
    common/               # Shared public utilities (e.g. ping)
    errors.py             # Sample unified-error routes (optional for products)
  schemas/                # API contracts (JSON), not DB
  models/                 # SQLAlchemy tables
  services/               # Business logic
  core/                   # Config, DB, security, deps, exceptions, middleware, seed
alembic/                  # Migrations
docker-compose.yml        # PostgreSQL only
.env.example              # Local template (safe to commit)
.env.server.example       # Server template (safe to commit; copy to .env)
.env                      # Secrets (do not commit)
```

Convention: `api/` for HTTP, `schemas/` for JSON, `models/` for tables, `services/` for business logic, `core/` for shared infrastructure, `main.py` only wires things together. Business logic lives once; App vs admin only diverge at entry and auth.

## Request path

```text
Browser /docs
  → middleware (CORS, Request ID, timing)
  → Depends (common headers → Bearer → JWT.sub + aud → User → roles → pagination, Session)
  → route + Pydantic validation
  → services
  → success: { "code": 0, "message": "ok", "data": ... }
  → failure: same envelope; codes like 40100 / 40300 / 40400 / 40900 / 42200 / 50000
  → writes must Session.commit()
  → PostgreSQL
```

- Health & docs: `/`, `/health`, `/docs` at root; no login
- App: `/api/v1/app/...`, `aud=app`, only `role=user` may log in
- Admin: `/api/v1/admin/...`, `aud=admin`, only `admin` / `operator`; no public register
- Common: `/api/v1/common/...`, public by default; shared authenticated routes use `Depends(get_current_account)`
- Identity: `Authorization: Bearer <access_token>`; authorization uses DB `role`, not JWT claims. Wrong-audience tokens fail at decode (401)
- Common headers on `/api/v1/*`: `X-Sign`, `X-Timestamp`, `X-Channel`. Missing/invalid values are currently allowed (logged only). Use `Depends(get_common_headers)` when needed
- Refresh sessions store `jti` in `refresh_sessions`; refresh rotates (old refresh dies); logout revokes refresh only. Access tokens stay stateless until expiry (default 30 minutes)
- App allows multi-device sessions; each admin login kicks other admin sessions for that account
- Failed logins are counted per username + client; over `LOGIN_MAX_ATTEMPTS` returns 429

## Response envelope

Success:

```json
{ "code": 0, "message": "ok", "data": {} }
```

List `data` wraps `items`, `total`, `page`, `page_size`. Validation failures use HTTP 422 and `code=42200` with field errors in `data.errors`. Unhandled exceptions return a generic internal error; stacks stay in logs; responses include `X-Request-ID`.

Users have phone, nickname, avatar, `updated_at`; soft delete via `deleted_at`. Username / email / phone are unique among non-deleted users. Soft-deleted accounts are ignored by query, login, and auth.

## Local setup

Needs: Python 3.13+, [uv](https://docs.astral.sh/uv/), Docker Desktop. Keep host Postgres port **5500** free.

```powershell
cd hemu_oversea_fastapi

uv sync
Copy-Item .env.example .env
# Set SECRET_KEY and BOOTSTRAP_PASSWORD to values you control

docker compose up -d
docker compose ps
# postgres should be healthy; host mapping like 0.0.0.0:5500->5432/tcp

alembic upgrade head

.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8600
```

`--reload-dir app` watches app code only (not `.venv`).

Open:

- [http://127.0.0.1:8600/health](http://127.0.0.1:8600/health)
- [http://127.0.0.1:8600/docs](http://127.0.0.1:8600/docs)

Startup seeds the bootstrap user if missing. Wait for `Application startup complete` before opening `/docs`. If seed hangs or you see `ConnectionTimeout`, confirm Compose Postgres is `healthy`.

### Bootstrap account

On startup the platform admin is created/synced (skipped if already present; password synced from config):

| Username      | Password                         | Notes                                      |
| ------------- | -------------------------------- | ------------------------------------------ |
| `superadmin`  | value of `BOOTSTRAP_PASSWORD`    | Platform admin (`platform_admin`); login: `/api/v1/admin/auth/login` |

In `/docs`: call login → Authorize with the **access_token** (no `Bearer` prefix) → call protected APIs.

## Server deploy (summary)

Fuller ops notes may live under [`DEPLOY_README/`](../DEPLOY_README/) at the monorepo root. Summary of a typical production flow:

- App directory: `hemu_oversea_fastapi/` on the server
- systemd unit example name: `hemu-oversea-fastapi.service`
- Uvicorn: with Nginx, bind `127.0.0.1:8600`; Postgres via Docker Compose on host port `5500`
- Set production CORS / OAuth callback URLs to match your real public origin
- Prefer systemd over `nohup` for long-running processes

### First deploy (outline)

```bash
cd /path/to/your/checkout
git pull
cd hemu_oversea_fastapi

cp .env.server.example .env
# Edit .env: POSTGRES_PASSWORD, SECRET_KEY, BOOTSTRAP_PASSWORD, CORS_ORIGINS, etc.

sudo docker compose up -d
sudo docker compose ps    # postgres should be healthy

uv sync
uv run alembic upgrade head

# After installing the systemd unit (see below):
sudo systemctl enable --now hemu-oversea-fastapi
sudo systemctl status hemu-oversea-fastapi
curl -sS http://127.0.0.1:8600/health
```

Open security group **80/443** for Nginx. Do **not** expose Postgres `5500` to the public internet. After Nginx is in place you can close public `8600`.

### systemd unit example

File: `/etc/systemd/system/hemu-oversea-fastapi.service` (adjust paths and `User=`):

```ini
[Unit]
Description=HeMu Oversea FastAPI
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=www
WorkingDirectory=/path/to/your/checkout/hemu_oversea_fastapi
EnvironmentFile=-/path/to/your/checkout/hemu_oversea_fastapi/.env
ExecStart=/path/to/your/checkout/hemu_oversea_fastapi/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8600 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hemu-oversea-fastapi
```

Do **not** use `--reload` in production. Without Nginx, you may temporarily bind `--host 0.0.0.0` and open `8600` in the security group.

### Release flow

```text
Push from workstation
  → server git pull
  → uv sync if dependencies changed
  → alembic upgrade head if migrations changed
  → systemctl restart hemu-oversea-fastapi
  → health check / logs
```

| Change type                         | Server steps                                              |
| ----------------------------------- | --------------------------------------------------------- |
| App code only                       | `git pull` → `restart`                                    |
| Dependencies (`pyproject` / lock)   | `git pull` → `uv sync` → `restart`                        |
| DB migrations                       | `git pull` → (optional) `uv sync` → `alembic upgrade head` → `restart` |
| Server `.env` only                  | save → `restart` (no pull)                                |

### Useful commands

**systemd**

```bash
sudo systemctl status hemu-oversea-fastapi
sudo systemctl restart hemu-oversea-fastapi
sudo journalctl -u hemu-oversea-fastapi -f
```

**Deps & migrations**

```bash
uv sync
uv run alembic upgrade head
uv run alembic current
```

**Postgres (Docker)**

```bash
sudo docker compose ps
sudo docker compose logs -f postgres --tail=100
```

**Health**

```bash
curl -sS http://127.0.0.1:8600/health
# Via your reverse proxy, e.g.:
# curl -sS https://your-domain.example/api/v1/common/ping
```

## Main APIs

| Method | Path                                       | Auth                                                      |
| ------ | ------------------------------------------ | --------------------------------------------------------- |
| GET    | `/health`                                  | Public                                                    |
| GET    | `/api/v1/common/ping`                      | Public                                                    |
| POST   | `/api/v1/app/auth/register`                | Public                                                    |
| POST   | `/api/v1/app/auth/login`                   | Public (user only)                                        |
| POST   | `/api/v1/app/auth/refresh`                 | Public (App refresh in body)                              |
| POST   | `/api/v1/app/auth/logout`                  | Refresh in body                                           |
| POST   | `/api/v1/app/auth/logout-all`              | App login; revoke all App sessions                        |
| POST   | `/api/v1/app/auth/password`                | App login; password change kicks all sessions             |
| GET    | `/api/v1/app/users/me`                     | App login                                                 |
| DELETE | `/api/v1/app/users/me`                     | App login; soft-delete self                               |
| POST   | `/api/v1/admin/auth/login`                 | Public (admin / operator)                                 |
| POST   | `/api/v1/admin/auth/refresh`               | Public (admin refresh in body)                            |
| POST   | `/api/v1/admin/auth/logout`                | Refresh in body                                           |
| POST   | `/api/v1/admin/auth/logout-all`            | Admin login; revoke all admin sessions                    |
| POST   | `/api/v1/admin/auth/password`              | Admin login; password change kicks all sessions           |
| GET    | `/api/v1/admin/users`                      | admin + operator; `page`, `page_size`, `keyword`, `role`  |
| POST   | `/api/v1/admin/users`                      | admin only                                                |
| PATCH  | `/api/v1/admin/users/{user_id}/status`     | admin + operator                                          |
| PATCH  | `/api/v1/admin/users/{user_id}/role`       | admin only                                                |
| POST   | `/api/v1/admin/users/{user_id}/password`   | admin only                                                |
| DELETE | `/api/v1/admin/users/{user_id}`            | admin only; soft delete                                   |

`/api/v1/errors/*` is for exercising the unified error envelope and may be removed in product code.

## Schema changes

Always: edit `app/models/` → `alembic revision --autogenerate -m "..."` → review the script (especially drops) → `alembic upgrade head`.

Do not edit already-applied revisions; do not rely on `create_all()` alone. Import every model in `app/models/__init__.py` so autogenerate sees new tables.

## Extension guide

1. **New App API**: `app/api/app/`, `Depends(get_current_app_user)`, register in `api/app/__init__.py`.
2. **New admin API**: `app/api/admin/`, `Depends(require_platform_admin)` or `require_admin_user`, register in `api/admin/__init__.py`.
3. **Shared utilities**: identical public rules → `app/api/common/`; shared authenticated → `Depends(get_current_account)`. Different auth/params → split app/admin routes; keep one service.
4. **New table**: one file under `app/models/`, inherit `Base`, then migrate.
5. **I/O models**: `app/schemas/`; never return password hashes.
6. **Writes**: `app/services/` with `Depends(get_db)` and `commit()`.
7. **Lists**: `Depends(get_pagination)` → `ApiResponse[PageData[...]]`.
8. **Config**: add `Settings` fields and `.env` / `.env.example`; restart Uvicorn after `.env` changes.
9. **Common headers**: set on the client; parse via `get_common_headers`, not per-route.

## Deferred (not in v1)

- Real validation for common headers (signature, time window, channel allowlist)
- Dedicated pytest database
- Celery + Redis, object storage, button-level permission tables

## Config highlights

| Variable                                              | Purpose                                                                 |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| `POSTGRES_USER` / `PASSWORD` / `DB` / `HOST` / `PORT` | Shared by Compose and app; builds DSN when `DATABASE_URL` is unset      |
| `DATABASE_URL` (optional)                             | Overrides assembled DSN (e.g. managed Postgres)                         |
| `SECRET_KEY`                                          | Signs JWTs; never commit real values                                    |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_MINUTES`         | Login failure rate limit                                                |
| `CORS_ORIGINS`                                        | JSON array of allowed frontend origins; restart after change            |
| `BOOTSTRAP_PASSWORD`                                  | Password for seed user `superadmin`                                     |

`.env` is gitignored. Prefer DBeaver / `psql` for GUI access; older Navicat builds may not work well with PostgreSQL 16.
