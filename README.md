# 合木海外 hemu_oversea_fullstack

合木海外的前后端合仓：FastAPI 后端 + Ant Design Pro 管理端。

- 管理端：供应商、店铺巡检与授权、商品与类目、人员、账号设置、敦煌网 OAuth 回调
- 服务端：鉴权（App / 管理端分 aud）、RBAC、用户管理、敦煌网对接、统一响应

```text
hemu_oversea_fullstack/
├── hemu_oversea_fastapi/        # Python FastAPI
└── hemu_oversea_fastapiadmin/   # Ant Design Pro（Umi Max 4）
```

---

## 环境要求

| 端 | 要求 |
| --- | --- |
| 后端 | Python 3.13+、[uv](https://docs.astral.sh/uv/)、Docker Desktop |
| 前端 | Node.js 22+、npm |

克隆后不要提交本机密钥。后端复制 `hemu_oversea_fastapi/.env.example` 为 `.env`。

---

## 后端 hemu_oversea_fastapi

本机 **5500**（Postgres）不要被占用。API 默认 **8600**（避免与管理端开发端口 8000 冲突）。

```powershell
cd hemu_oversea_fastapi
uv sync
Copy-Item .env.example .env

docker compose up -d
alembic upgrade head

.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8600
```

- 探活：http://127.0.0.1:8600/health
- 文档：http://127.0.0.1:8600/docs

种子账号：`admin` / `admin123456`（管理端）、`operator` / `operator123456`、`user` / `user123456`（App）。

更完整的接口与配置说明见 [hemu_oversea_fastapi/README.md](hemu_oversea_fastapi/README.md)。

---

## 前端 hemu_oversea_fastapiadmin

开发服务器默认 **8000**。`config/proxy.ts` 会把 `/api/` 转到后端；本地联调时把 `target` 改成与 Uvicorn 一致的地址（例如 `http://127.0.0.1:8600`）。

```powershell
cd hemu_oversea_fastapiadmin
npm install
npm start
```

打开：http://localhost:8000

管理端登录走 `/api/v1/admin/auth/login`，使用后端种子账号 `admin` / `admin123456`（需图形验证码）。

前端脚手架与模块说明见 [hemu_oversea_fastapiadmin/README.md](hemu_oversea_fastapiadmin/README.md)。

---

## 不要提交

- `hemu_oversea_fastapi/.env`（数据库、JWT、敦煌网密钥等）
- `.venv/`、`node_modules/`、`dist/`、`.umi/`
- 数据库备份 `*.sql`

远程仓库：https://gitcode.com/superman_1024/hemu_oversea_fullstack
