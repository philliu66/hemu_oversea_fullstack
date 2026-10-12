# hemu_oversea_fastapi

HeMu 海外业务 **FastAPI 后端**。基于 FastAPI 脚手架起步，已包含环境、PostgreSQL、分层、配置、统一响应与异常、JWT 鉴权、RBAC、CORS 与 Request ID。

HTTP 入口按客户端拆成 **App**、**管理端**、**公共**；`services/` / `models/` 仍共用。JWT 带 `aud`（`app` / `admin`），两端 token 不能互调。refresh 入库并可撤销；登录失败会限流。

签名、时间戳、渠道已走公共 Header（`X-Sign` / `X-Timestamp` / `X-Channel`），目前只解析打日志、不校验。pytest 独立测试库尚未接入。

## 技术栈

- Python 3.13+、uv、Uvicorn
- FastAPI + Pydantic v2 + pydantic-settings
- PostgreSQL 16（Docker Compose）+ SQLAlchemy 2.0 + Alembic + psycopg v3
- JWT（access + refresh，含受众 `aud`）+ Argon2 密码哈希
- 角色：`admin` / `operator` / `user`

## 目录

```text
app/
  main.py                 # 装配：lifespan、中间件、挂路由
  api/                    # HTTP 接口（按客户端分叉）
    router.py             # 汇总 app / admin / common，统一前缀 /api/v1
    health.py             # GET /health（根路径，探活）
    app/                  # App：注册、登录、刷新、登出、改密、/users/me
    admin/                # 管理端：登录、刷新、登出、改密、ping、用户列表（无公开注册）
    common/               # 两端都可调的公开工具，如 ping
    errors.py             # 联调统一响应，业务项目可删
  schemas/                # API 合同（JSON），不是数据库
  models/                 # SQLAlchemy 表
  services/               # 业务（登录会话、创建用户、列表查询）
  core/                   # 配置、数据库、安全、依赖、异常、中间件、种子
alembic/                  # 迁移脚本
docker-compose.yml        # 仅启动 PostgreSQL
.env.example              # 本机配置样例（可进 Git）
.env.server.example       # 服务器配置模板（可进 Git；复制为 .env 后填必改项）
.env                      # 本机/服务器密钥（不进 Git）
```

约定：`api/` 对 HTTP，`schemas/` 对 JSON，`models/` 对表，`services/` 对业务，`core/` 对全站配件，`main.py` 只组装。业务逻辑只写一份；App 与管理端只拆入口和鉴权。

## 请求路径

```text
浏览器 /docs
  → 中间件（CORS、Request ID、耗时）
  → Depends（公共 Header → Bearer → JWT.sub + aud → 查 User → require_roles → 分页、Session）
  → 路由 + Pydantic 校验
  → services
  → 成功：{ "code": 0, "message": "ok", "data": ... }
  → 失败：同一外壳，code 为 40100 / 40300 / 40400 / 40900 / 42200 / 50000 等
  → 写操作必须 Session.commit()
  → PostgreSQL
```

- 探活、文档：`/`、`/health`、`/docs` 在根路径，无需登录
- App：`/api/v1/app/...`，token 的 `aud=app`，仅 `role=user` 可登录
- 管理端：`/api/v1/admin/...`，token 的 `aud=admin`，仅 `admin` / `operator` 可登录；无公开注册
- 公共：`/api/v1/common/...`，默认公开；两端同权且需登录时用 `Depends(get_current_account)`
- 身份：`Authorization: Bearer <access_token>`；权限以用户表 `role` 为准，不写进 JWT。错端 token 在解码阶段 401
- 公共 Header（`/api/v1/*`）：`X-Sign`（字符串）、`X-Timestamp`（字符串）、`X-Channel`（整数）。axios 拦截器加在 Header，业务字段仍放 JSON body。当前缺省或格式不对都放行，只打日志；接口里需要时用 `Depends(get_common_headers)`
- refresh 以 `jti` 写入 `refresh_sessions`：刷新会轮换（旧 refresh 立刻失效）；登出只作废 refresh。access 仍无状态，登出后最多还能用到过期（默认 30 分钟）
- App 允许多设备同时在线；管理端每次登录会踢掉该账号其它管理端会话
- 登录失败按用户名+端统计，超过 `LOGIN_MAX_ATTEMPTS` 返回 429

## 统一响应

成功：

```json
{ "code": 0, "message": "ok", "data": {} }
```

列表的 `data` 再套 `items`、`total`、`page`、`page_size`。校验失败 HTTP 422、`code=42200`，`data.errors` 能对上字段名。未处理异常对外只返回「服务器内部错误」，堆栈只打日志，响应带 `X-Request-ID`。

用户表含手机号、昵称、头像、`updated_at`；删除用 `deleted_at` 软删除，未删除用户的用户名/邮箱/手机号唯一。查询、登录、鉴权都忽略已软删账号。

## 从零运行

需要：Python 3.13+、[uv](https://docs.astral.sh/uv/)、Docker Desktop。本机 **5432** 不要被其它 Postgres 占用。

```powershell
cd e:\personal\projects\HeMuOversea\code\hemu_oversea_fastapi

uv sync
Copy-Item .env.example .env
# 把 SECRET_KEY 改成长随机串

docker compose up -d
docker compose ps
# postgres 应为 healthy，且有 0.0.0.0:5432->5432/tcp

alembic upgrade head

.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8600
```

`--reload-dir app` 只监视应用代码，不要监视 `.venv`。

打开：

- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

启动时会写入种子用户（已存在则跳过）。日志出现 `Application startup complete` 后再打开 `/docs`。若启动卡在播种或报 `ConnectionTimeout`，先确认 Compose 里 Postgres 已 `healthy`。

### 种子账号

启动时仅写入超级管理员（已存在则跳过创建，并按配置同步密码）：

| 用户名         | 密码                   | 说明                                      |
| ----------- | -------------------- | --------------------------------------- |
| `superadmin` | `BOOTSTRAP_PASSWORD`（默认 `123456`） | 平台超管，走 `/api/v1/admin/auth/login` |

`/docs` 中：login → Authorize 粘贴 **access_token**（不要带 `Bearer` 前缀）→ 再调需登录接口。

## 服务器部署与运维

更完整的架构、安全组、Nginx、迁移说明见仓库根目录 [`DEPLOY_README/`](../DEPLOY_README/)。下文为当前线上常用流程摘要。

约定：

- 应用目录：服务器上的 `hemu_oversea_fastapi/`（下文以该目录为 cwd）
- systemd 单元名：`hemu-oversea-fastapi.service`
- Uvicorn：有 Nginx 时监听 `127.0.0.1:8600`；Postgres 用 Docker Compose，映射本机 `5500`
- 正式域名示例：`https://hemuoversea.xiaohemu.net`（CORS / OAuth 回调与地址栏一致）
- **不要**用 `nohup` 作为正式常驻方案

### 首次上线（摘要）

```bash
cd /你的仓库路径
git pull
cd hemu_oversea_fastapi

cp .env.server.example .env
# 编辑 .env：POSTGRES_PASSWORD、SECRET_KEY、BOOTSTRAP_PASSWORD、CORS_ORIGINS 等

sudo docker compose up -d
sudo docker compose ps    # postgres 应为 healthy

uv sync
uv run alembic upgrade head

# 配置并启动 systemd（见下方单元示例）后：
sudo systemctl enable --now hemu-oversea-fastapi
sudo systemctl status hemu-oversea-fastapi
curl -sS http://127.0.0.1:8600/health
```

安全组放行 **80/443**（Nginx）；**不要**对公网开放 Postgres `5500`。有 Nginx 后公网可关掉 `8600`。

### systemd 单元示例

文件：`/etc/systemd/system/hemu-oversea-fastapi.service`（路径、`User=` 按实机修改）：

```ini
[Unit]
Description=HeMu Oversea FastAPI
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=www
WorkingDirectory=/你的仓库路径/hemu_oversea_fastapi
EnvironmentFile=-/你的仓库路径/hemu_oversea_fastapi/.env
ExecStart=/你的仓库路径/hemu_oversea_fastapi/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8600 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

首次写入或修改该文件后：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hemu-oversea-fastapi
```

生产 **不要**加 `--reload`。无 Nginx、需公网直连 API 时，可将 `--host` 临时改为 `0.0.0.0`，并放行安全组 `8600`。

### 后续发版顺序

```text
本机推送 Git
  → 服务器 git pull
  → 有依赖变化则 uv sync
  → 有表结构变化则 alembic upgrade head
  → systemctl restart hemu-oversea-fastapi
  → 探活 / 看日志
```

| 变更类型 | 服务器操作 |
|----------|------------|
| 仅业务代码 | `git pull` → `restart` |
| 依赖（`pyproject.toml` / lock） | `git pull` → `uv sync` → `restart` |
| 数据库迁移 | `git pull` →（如需）`uv sync` → `alembic upgrade head` → `restart` |
| 仅改服务器 `.env` | 保存后 `restart`（无需 pull） |

日常发版示例：

```bash
cd /你的仓库路径
git pull
cd hemu_oversea_fastapi

uv sync                          # 依赖无变可跳过
uv run alembic upgrade head      # 无新迁移可跳过

sudo systemctl restart hemu-oversea-fastapi
sudo systemctl status hemu-oversea-fastapi
curl -sS http://127.0.0.1:8600/health
```

### 常用命令

**systemd（FastAPI）**

```bash
sudo systemctl status hemu-oversea-fastapi
sudo systemctl start hemu-oversea-fastapi
sudo systemctl stop hemu-oversea-fastapi
sudo systemctl restart hemu-oversea-fastapi
sudo journalctl -u hemu-oversea-fastapi -f
sudo journalctl -u hemu-oversea-fastapi -n 100 --no-pager
```

**依赖与迁移**

```bash
uv sync
uv run alembic upgrade head
uv run alembic current
```

**Postgres（Docker）**

```bash
sudo docker compose ps
sudo docker compose logs -f postgres --tail=100
sudo docker compose restart postgres   # 一般很少需要
```

**探活**

```bash
curl -sS http://127.0.0.1:8600/health
# 经 Nginx 的接口示例（路径以实际为准）：
curl -sS https://hemuoversea.xiaohemu.net/api/v1/common/ping
```

**Nginx（仅改了反代配置时）**

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 主要接口


| 方法     | 路径                                       | 鉴权                                                      |
| ------ | ---------------------------------------- | ------------------------------------------------------- |
| GET    | `/health`                                | 公开                                                      |
| GET    | `/api/v1/common/ping`                    | 公开（App / 管理端都可调）                                        |
| POST   | `/api/v1/app/auth/register`              | 公开                                                      |
| POST   | `/api/v1/app/auth/login`                 | 公开（仅 user）                                              |
| POST   | `/api/v1/app/auth/refresh`               | 公开（body 里用 App 的 refresh）                               |
| POST   | `/api/v1/app/auth/logout`                | body 里用 refresh                                         |
| POST   | `/api/v1/app/auth/logout-all`            | App 登录，作废该用户全部 App 会话                                   |
| POST   | `/api/v1/app/auth/password`              | App 登录；改密后踢掉所有会话                                        |
| GET    | `/api/v1/app/users/me`                   | App 登录                                                  |
| DELETE | `/api/v1/app/users/me`                   | App 登录，注销自己（软删除）                                        |
| POST   | `/api/v1/admin/auth/login`               | 公开（仅 admin / operator）                                  |
| POST   | `/api/v1/admin/auth/refresh`             | 公开（body 里用管理端 refresh）                                  |
| POST   | `/api/v1/admin/auth/logout`              | body 里用 refresh                                         |
| POST   | `/api/v1/admin/auth/logout-all`          | 管理端登录，作废该账号全部管理端会话                                      |
| POST   | `/api/v1/admin/auth/password`            | 管理端登录；改密后踢掉所有会话                                         |
| GET    | `/api/v1/admin/users`                    | admin + operator；支持 `page`、`page_size`、`keyword`、`role` |
| POST   | `/api/v1/admin/users`                    | 仅 admin；可指定角色、是否启用                                      |
| PATCH  | `/api/v1/admin/users/{user_id}/status`   | admin + operator；启用/停用，停用会踢会话，不能操作自己                    |
| PATCH  | `/api/v1/admin/users/{user_id}/role`     | 仅 admin；改角色并踢会话，不能改自己                                   |
| POST   | `/api/v1/admin/users/{user_id}/password` | 仅 admin；重置密码并踢会话，不能重置自己                                 |
| DELETE | `/api/v1/admin/users/{user_id}`          | 仅 admin；软删除，不能删自己                                       |


`/api/v1/errors/`* 仅用于联调统一响应，业务项目可删。

## 改表

永远走：改 `app/models/` → `alembic revision --autogenerate -m "说明"` → 检查脚本（尤其 `drop_column`）→ `alembic upgrade head`。

不要改已经执行过的旧脚本，不要只用 `create_all()` 或只在客户端里改表。`app/models/__init__.py` 必须 import 所有 Model，否则 autogenerate 看不到新表。

## 扩展指南

1. **新 App 接口**：`app/api/app/`，`Depends(get_current_app_user)`，在 `api/app/__init__.py` 里 `include_router`。
2. **新管理端接口**：`app/api/admin/`，`Depends(require_super_admin)` 或 `require_admin_user`，在 `api/admin/__init__.py` 里挂上。
3. **两端都可调的工具**：规则完全一样且公开 → `app/api/common/`；需登录且两端同权 → `Depends(get_current_account)`。权限或入参不同则拆成 app / admin 两条路由，`services/` 仍共用。
4. **新表**：`app/models/` 一表一文件，继承 `Base`，再走迁移。
5. **入参/出参**：`app/schemas/`，创建和对外展示拆开；密码哈希不要进响应。
6. **写库**：放 `app/services/`，路由里 `Depends(get_db)`，写操作必须 `commit()`。不要按客户端复制一份 service。
7. **列表**：`Depends(get_pagination)`，返回 `ApiResponse[PageData[...]]`。
8. **配置**：只加 `Settings` 字段和 `.env` / `.env.example`，改 `.env` 后重启 Uvicorn。
9. **公共 Header**：axios 加 `X-Sign` / `X-Timestamp` / `X-Channel`；解析在 `get_common_headers`，不要在每个路由里读 Header。

## 预留、第一期不做

- 公共 Header 的真实校验：签名、时间窗、渠道白名单（现在只解析打日志）
- pytest 独立库
- Celery + Redis、对象存储、按钮级权限表

## 配置要点


| 变量                                            | 作用                                               |
| --------------------------------------------- | ------------------------------------------------ |
| `POSTGRES_USER` / `PASSWORD` / `DB` / `HOST` / `PORT` | Compose 与应用共用；未设 `DATABASE_URL` 时组装为 `postgresql+psycopg://...` |
| `DATABASE_URL`（可选）                        | 非空时覆盖上面的组装结果（如 RDS） |
| `SECRET_KEY`                                  | 签 JWT，不要提交真实值                                    |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_MINUTES` | 登录失败限流：窗口内次数与分钟数                                 |
| `CORS_ORIGINS`                                | JSON 数组，前端源；改完须重启                                |
| `BOOTSTRAP_PASSWORD`                          | 种子账号 `superadmin` 密码；启动时写入或同步                     |


`.env` 已在 `.gitignore`。图形客户端连库建议 DBeaver / `psql`；Navicat 15 无法正常浏览 PostgreSQL 16。