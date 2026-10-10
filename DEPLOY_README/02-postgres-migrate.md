# 02 — PostgreSQL（Docker）上云与数据迁移

## 目标

在阿里云服务器上使用与本地相同的 `hemu_oversea_fastapi/docker-compose.yml` 跑 PostgreSQL 16，并按需把本地库数据迁过去。

Compose 摘要：

- 镜像：`postgres:16`
- 容器名：`hemu_oversea_fastapi_postgres`
- 默认库：`hemu_oversea_fastapi`
- 端口：`5500:5432`
- 数据卷：`postgres_data`

## 1. 服务器启动 Postgres

前置：服务器已安装 Docker / Docker Compose 插件。

```bash
cd /opt/hemu_oversea_fastapi   # 按你的实际代码路径调整
docker compose up -d
docker compose ps
# postgres 应为 healthy，且有 0.0.0.0:5500->5432/tcp（仅本机访问即可）
```

生产环境请修改 Compose 中的 `POSTGRES_PASSWORD`（及用户/库名如有变更），并保证与 `.env` 中 `DATABASE_URL` 一致。不要长期使用示例密码 `postgres/postgres`。

## 2. 从本机迁移数据

### 方式 A：自定义格式 dump（推荐）

**本机（Windows PowerShell，容器 healthy 时）：**

```powershell
cd e:\personal\projects\HeMuOversea\code\hemu_oversea_fastapi

docker exec hemu_oversea_fastapi_postgres pg_dump -U postgres -d hemu_oversea_fastapi -F c -f /tmp/hemu.dump
docker cp hemu_oversea_fastapi_postgres:/tmp/hemu.dump .\hemu.dump
```

将 `hemu.dump` 传到服务器（scp / 对象存储等），然后在服务器执行：

```bash
docker cp hemu.dump hemu_oversea_fastapi_postgres:/tmp/hemu.dump
docker exec -i hemu_oversea_fastapi_postgres \
  pg_restore -U postgres -d hemu_oversea_fastapi --clean --if-exists /tmp/hemu.dump
```

若出现扩展/权限类告警，可评估后改用方式 B。

### 方式 B：纯 SQL

**本机：**

```powershell
docker exec hemu_oversea_fastapi_postgres pg_dump -U postgres -d hemu_oversea_fastapi > hemu.sql
```

**服务器：**

```bash
docker exec -i hemu_oversea_fastapi_postgres psql -U postgres -d hemu_oversea_fastapi < hemu.sql
```

### 方式 C：不迁业务数据（空库）

```bash
docker compose up -d
# 应用侧
uv sync
alembic upgrade head
# 启动应用后会写入种子用户（已存在则跳过）
```

## 3. 配置是否要改？

### 代码

FastAPI 与 Postgres **同机**部署时，应用代码一般**不需要**为连库而改动；连接串仍走 Settings / `.env`。

### 服务器 `.env`（必须单独配置，勿提交 Git）

本地示例（`hemu_oversea_fastapi/.env.example`）：

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5500/hemu_oversea_fastapi
```

| 场景 | `DATABASE_URL` |
|------|----------------|
| FastAPI 与 Docker Postgres 同机 | 可用 `localhost:5500`（与本地结构相同） |
| 使用阿里云 RDS 或其他主机 | 改为 RDS/内网地址与端口 |
| 生产密码 | 必须改强密码，并与 Compose/`POSTGRES_PASSWORD` 一致 |

除数据库外，上线至少检查：

```env
DATABASE_URL=postgresql+psycopg://postgres:强密码@localhost:5500/hemu_oversea_fastapi

SECRET_KEY=换成很长的随机串

# 必须与浏览器地址栏一致（协议+主机+端口）
CORS_ORIGINS=["http://你的公网IP","http://你的公网IP:8000"]

# 若使用敦煌 OAuth，回调必须改为公网可访问地址
DHGATE_REDIRECT_URI=http://你的公网IP/api/v1/common/oauth/dhgate/callback
DHGATE_FRONTEND_REDIRECT_URI=http://你的前端公网地址/callback
```

改 `.env` 后需重启 Uvicorn。`CORS_ORIGINS` 不匹配会导致浏览器跨域失败。

### 安全

- 安全组**不要**对公网开放 `5500`
- dump 文件可能含敏感数据，传输后及时删除服务器与本地临时文件
- `SECRET_KEY`、库密码、敦煌密钥不要写进仓库

## 4. 迁移后快速校验

```bash
docker exec -it hemu_oversea_fastapi_postgres \
  psql -U postgres -d hemu_oversea_fastapi -c '\dt'
```

确认表存在后，再执行应用侧 `alembic upgrade head`（若 dump 已是最新 schema，通常为 no-op 或仅补齐差额）。

## 下一步

- 部署 FastAPI 进程 → [03-fastapi-deploy.md](./03-fastapi-deploy.md)
