# HeMu Oversea FastAPI — 阿里云部署须知

本文说明如何将 `hemu_oversea_fastapi` 部署到阿里云 ECS，使管理端/前端可通过公网 IP（或域名）访问后端 API。

本目录与仓库根目录 [`README.md`](../README.md) 同级，只覆盖**生产/公网部署**。后端本地开发见 [`hemu_oversea_fastapi/README.md`](../hemu_oversea_fastapi/README.md)。

## 文档索引

| 文档 | 内容 |
|------|------|
| [01-overview.md](./01-overview.md) | 目标架构、端口与安全组 |
| [02-postgres-migrate.md](./02-postgres-migrate.md) | Docker Postgres 上云与数据迁移、`.env` 变更 |
| [03-fastapi-deploy.md](./03-fastapi-deploy.md) | FastAPI 部署步骤、systemd（不推荐长期用 nohup） |
| [04-nginx-frontend.md](./04-nginx-frontend.md) | Nginx 反代与前端对接 |
| [05-checklist.md](./05-checklist.md) | 上线检查清单与常见问题 |

## 推荐路径（最短可用）

1. ECS 安装 Docker、Python 3.13+、[uv](https://docs.astral.sh/uv/)、Nginx（可选）
2. 上传/拉取代码 → 进入 `hemu_oversea_fastapi/` → `docker compose up -d` 启动 Postgres
3. 按需从本机 `pg_dump` 迁数据（见 [02](./02-postgres-migrate.md)）
4. 配置服务器 `hemu_oversea_fastapi/.env`（密钥、CORS、OAuth 回调等）
5. 在 `hemu_oversea_fastapi/` 下 `uv sync` → `alembic upgrade head` → **systemd** 启动 Uvicorn
6. 安全组放行 80/443（或临时放行 API 端口做联调）；**不要**对公网开放 Postgres `5500`
7. 用 Nginx 反代（推荐）并配置前端 `baseURL`（见 [04](./04-nginx-frontend.md)）
8. 按 [05](./05-checklist.md) 验收 `/health`、`/docs` 与登录

## 明确不推荐

- 用 `nohup uvicorn ... &` 作为正式常驻方案（进程挂掉不拉起、重启需手动、日志与多 worker 难管）。临时验证可用，正式环境请用 **systemd**（或后续 Docker 化应用）。
- 安全组对公网开放 `5500`（Postgres）。
- 生产继续使用默认密码（`.env` 中 `POSTGRES_PASSWORD=postgres`）与示例 `SECRET_KEY`。
