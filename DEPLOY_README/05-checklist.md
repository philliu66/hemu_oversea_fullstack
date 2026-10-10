# 05 — 上线检查清单与常见问题

## 部署前

- [ ] ECS 已安装 Docker、Python 3.13+、uv；可选 Nginx
- [ ] 安全组：SSH（限办公 IP）、80/443；**未**对公网开放 `5500`
- [ ] 代码已放到服务器（如 `/opt/hemu_oversea_fastapi`）
- [ ] 服务器 `.env` 已配置且**未**提交到 Git
- [ ] `SECRET_KEY`、数据库密码已换成生产值
- [ ] `CORS_ORIGINS` 与浏览器实际访问源一致
- [ ] 如需敦煌 OAuth：回调地址已改为公网，并与开放平台配置一致

## 数据库

- [ ] `docker compose up -d` 且 Postgres `healthy`
- [ ] 已迁移数据（dump/restore）或确认空库可接受
- [ ] `alembic upgrade head` 成功
- [ ] `\dt` 可见业务表

## 应用进程

- [ ] `uv sync` 成功
- [ ] systemd 单元路径、`WorkingDirectory`、`ExecStart` 正确
- [ ] `systemctl enable --now hemu-fastapi` 成功
- [ ] `curl http://127.0.0.1:8600/health` 正常
- [ ] 生产**未**开启 `--reload`
- [ ] **未**依赖 nohup 作为正式方案

## 网关与前端

- [ ] Nginx 配置已 `nginx -t` 并通过 reload
- [ ] 公网可访问 `/health`（经 80 或临时 8600）
- [ ] `/docs` 可打开（生产可按需关闭文档路由，属后续加固）
- [ ] 前端 `baseURL` 或同域反代已配置
- [ ] 浏览器登录管理端成功；Network 中 API 无 CORS 报错

## 验收命令速查

```bash
# 本机环回
curl -sS http://127.0.0.1:8600/health

# 经 Nginx
curl -sS http://127.0.0.1/health

# 进程
sudo systemctl status hemu-fastapi
sudo journalctl -u hemu-fastapi -n 100 --no-pager

# 数据库
docker compose -f /opt/hemu_oversea_fastapi/docker-compose.yml ps
```

## 常见问题

### 1. 外网打不开 API

- 安全组是否放行对应端口（80 或 8600）
- Uvicorn 是否绑在 `127.0.0.1` 却无 Nginx；直连公网需 `0.0.0.0` 或走 Nginx
- 云厂商是否还有防火墙（firewalld/ufw）拦截

### 2. 前端 CORS 报错

- 检查 `.env` 的 `CORS_ORIGINS` 是否**完整**匹配前端源（含协议与端口）
- 改完 `.env` 后是否已 `systemctl restart hemu-fastapi`
- 同域反代时可减少对 CORS 的依赖

### 3. 数据库连接失败 / 启动卡在播种

- `docker compose ps` 是否 healthy
- `DATABASE_URL` 主机/端口/密码是否与 Compose 一致（同机一般为 `localhost:5500`）
- 应用是否在 Postgres 就绪前启动（可重启一次 hemu-fastapi）

### 4. 本机有数据，云上是空的

- 是否执行了 [02](./02-postgres-migrate.md) 的 dump/restore
- restore 目标库名是否为 `hemu_oversea_fastapi`

### 5. OAuth 回调失败

- `DHGATE_REDIRECT_URI` / 前端落地地址是否公网可达
- 敦煌控制台白名单是否已同步
- HTTP/HTTPS 与端口是否一致

### 6. 机器重启后服务没了

- 是否只用了 nohup：改为 systemd 并 `enable`
- Postgres：Compose 已设 `restart: unless-stopped`，确认 Docker 开机自启

## 配置对照摘要

| 变量 | 作用 |
|------|------|
| `DATABASE_URL` | SQLAlchemy / Alembic；驱动 `postgresql+psycopg` |
| `SECRET_KEY` | JWT 签名；生产必须更换 |
| `CORS_ORIGINS` | JSON 数组；改完须重启 |
| `DHGATE_REDIRECT_URI` | 后端 OAuth 回调（公网） |
| `DHGATE_FRONTEND_REDIRECT_URI` | 前端授权落地页 |

仓库总览见根目录 [`README.md`](../README.md)；后端本地开发见 [`hemu_oversea_fastapi/README.md`](../hemu_oversea_fastapi/README.md)。
