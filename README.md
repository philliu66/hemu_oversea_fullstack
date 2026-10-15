# HeMu Oversea Fullstack

English | [简体中文](./README.zh.md)

Monorepo for HeMu Oversea: FastAPI backend + Ant Design Pro admin console.

- **Admin**: suppliers, shop inspection & authorization, products & categories, staff, account settings, DHgate OAuth callback
- **API**: auth (App / admin audiences), RBAC, user management, DHgate integration, unified response envelope

```text
hemu_oversea_fullstack/
├── hemu_oversea_fastapi/        # Python FastAPI
└── hemu_oversea_fastapiadmin/   # Ant Design Pro (Umi Max 4)
```

---

## Requirements

| Side     | Requirements                                                      |
| -------- | ----------------------------------------------------------------- |
| Backend  | Python 3.13+, [uv](https://docs.astral.sh/uv/), Docker Desktop    |
| Frontend | Node.js 22+, npm                                                  |

After cloning, do **not** commit local secrets. Copy `hemu_oversea_fastapi/.env.example` to `.env` and fill in your values.

---

## Backend (`hemu_oversea_fastapi`)

Keep host port **5500** (Postgres) free. API defaults to **8600** (avoids clashing with the admin dev server on 8000).

```powershell
cd hemu_oversea_fastapi
uv sync
Copy-Item .env.example .env

docker compose up -d
alembic upgrade head

.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8600
```

- Health: [http://127.0.0.1:8600/health](http://127.0.0.1:8600/health)
- Docs: [http://127.0.0.1:8600/docs](http://127.0.0.1:8600/docs)

Bootstrap admin username is `superadmin`. Password comes from `BOOTSTRAP_PASSWORD` in your local `.env` (see `.env.example`).

More API and config details: [hemu_oversea_fastapi/README.md](hemu_oversea_fastapi/README.md).

---

## Frontend (`hemu_oversea_fastapiadmin`)

Dev server defaults to **8000**. `config/proxy.ts` proxies `/api/` to the backend; for local work, keep `target` aligned with Uvicorn (e.g. `http://127.0.0.1:8600`).

```powershell
cd hemu_oversea_fastapiadmin
npm install
npm start
```

Open: [http://localhost:8000](http://localhost:8000)

Admin login uses `/api/v1/admin/auth/login` with the backend bootstrap account (captcha required).

Frontend notes: [hemu_oversea_fastapiadmin/README.md](hemu_oversea_fastapiadmin/README.md).

---

## Do not commit

- `hemu_oversea_fastapi/.env` (database, JWT, third-party credentials, etc.)
- `.venv/`, `node_modules/`, `dist/`, `.umi/`
- Database dumps such as `*.sql`
