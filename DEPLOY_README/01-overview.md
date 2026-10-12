# 01 — 目标架构与网络

## 推荐架构

```text
浏览器 / 前端
  → 公网 IP:80/443（安全组放行）
  → Nginx（强烈建议）
  → Uvicorn :8600（建议只监听本机 127.0.0.1，由 Nginx 转发）
  → Docker Postgres 宿主机 :5500 → 容器 5432（不要对公网开放）
```

当前工程特点（与部署相关）：

- 后端目录：`hemu_oversea_fastapi/`；管理端：`hemu_oversea_fastapiadmin/`
- `hemu_oversea_fastapi/docker-compose.yml` **只**启动 PostgreSQL 16；用户/密码/库名/宿主机端口来自 `.env` 的 `POSTGRES_*`（默认端口映射 `5500:5432`）
- FastAPI 本机开发常用：`uvicorn app.main:app --host 127.0.0.1 --port 8600`
- 配置全部来自 `hemu_oversea_fastapi/.env`（见 `.env.example`）
- 管理端开发态通过 Umi `proxy` 转到 `127.0.0.1:8600`；**生产没有 proxy**，必须配置 API 根地址或同域反代

## 端口约定

| 服务 | 本机开发 | 服务器建议 |
|------|----------|------------|
| Postgres（Docker） | `localhost:5500` | 同机仍用 `localhost:5500`；安全组**不**放行公网 |
| FastAPI / Uvicorn | `127.0.0.1:8600` | 生产可用 `127.0.0.1:8600` + Nginx；临时联调可 `0.0.0.0:8600` |
| Nginx | — | `80` / `443` 对公网 |

说明：后端本地 README 中探活示例曾写 `8000`，仓库根 README 约定 API 为 **8600**；以你实际启动端口为准，安全组、Nginx、前端 `baseURL` 必须一致。本部署文档统一按 **8600** 书写。

## 阿里云安全组建议

| 方向 | 端口 | 来源 | 说明 |
|------|------|------|------|
| 入站 | 22 | 你的办公 IP | SSH |
| 入站 | 80 / 443 | `0.0.0.0/0` | HTTP/HTTPS（有 Nginx 时） |
| 入站 | 8600 | 可选、临时 | 无 Nginx 时临时测 API；正式建议关掉 |
| 入站 | **5500** | **不要开放** | 仅本机 FastAPI 访问 |

## 两种前端访问方式

1. **只部署后端，前端仍在本机开发**  
   - 前端 `baseURL` 指向 `http://公网IP:8600`（或经 Nginx 的 `http://公网IP`）  
   - 服务器 `.env` 的 `CORS_ORIGINS` 需包含本机前端源（如 `http://localhost:8000`）

2. **前端也部署到服务器（或 CDN）**  
   - 推荐 Nginx 同域：静态页与 `/api` 同一主机 → `baseURL` 可继续为空字符串 `''`  
   - 若前后端不同源，必须配置正确的 `CORS_ORIGINS` 与前端 `baseURL`

## 下一步

- 数据库与数据迁移 → [02-postgres-migrate.md](./02-postgres-migrate.md)
- 应用进程部署 → [03-fastapi-deploy.md](./03-fastapi-deploy.md)
