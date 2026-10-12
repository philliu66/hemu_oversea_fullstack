# 03 — FastAPI 部署（systemd）

## 是否使用 nohup？

**不推荐**将 `nohup uvicorn ... &` 作为正式常驻方案。

| 方式 | 适用 | 问题 |
|------|------|------|
| `nohup` / 前台终端 | 临时验证公网能否通 | 崩溃不拉起、重启需手动、日志与 worker 难管 |
| **systemd**（本文推荐） | 个人/小团队正式部署 | 自动重启、开机自启、标准日志 |
| Docker Compose 再加 app 服务 | 后续演进 | 当前仓库 Compose 仅含 Postgres，可后续扩展 |
| Nginx 反代 | 强烈建议配合 systemd | 见 [04-nginx-frontend.md](./04-nginx-frontend.md) |

临时验证示例（**仅调试**）：

```bash
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8600 > /var/log/hemu-fastapi.log 2>&1 &
```

正式环境请改用下面的 systemd。

## 服务器前置

- Linux（常见：Alibaba Cloud Linux / Ubuntu）
- Python **3.13+**
- [uv](https://docs.astral.sh/uv/)
- Docker（用于 Postgres，见 [02](./02-postgres-migrate.md)）
- 代码目录示例：`/opt/hemu_oversea_fastapi`

## 部署步骤

```bash
cd /opt/hemu_oversea_fastapi

# 1. 环境文件（从本机安全拷贝或按 .env.example 新建，再改生产值）
cp .env.example .env
# 编辑 .env：POSTGRES_PASSWORD、SECRET_KEY、CORS_ORIGINS、DHGATE_* 等

# 2. 依赖
uv sync

# 3. 数据库已 healthy 后执行迁移
.venv/bin/alembic upgrade head
# 或：source .venv/bin/activate && alembic upgrade head

# 4. 先手工冒烟（确认能起再装 systemd）
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8600
# 另开终端：curl http://127.0.0.1:8600/health
# Ctrl+C 停掉后安装 systemd
```

生产注意：

- **不要**使用 `--reload`
- 若前面有 Nginx：Uvicorn 监听 `127.0.0.1:8600` 即可
- 若暂时无 Nginx、直接用公网 IP 访问 API：需 `--host 0.0.0.0`，并在安全组临时放行 `8600`

## systemd 单元示例

创建文件 `/etc/systemd/system/hemu-fastapi.service`：

```ini
[Unit]
Description=HeMu Oversea FastAPI
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hemu_oversea_fastapi
# 若希望由 systemd 注入环境，可使用 EnvironmentFile；
# 本项目 Settings 也会从 WorkingDirectory 下的 .env 读取。
EnvironmentFile=-/opt/hemu_oversea_fastapi/.env
ExecStart=/opt/hemu_oversea_fastapi/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8600 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

说明：

- `User=` 建议改为非 root 的专用用户，并保证对该目录与 `.env` 有读权限
- 无 Nginx、需公网直连时，把 `--host 127.0.0.1` 改为 `0.0.0.0`
- `--workers` 按 CPU 调整；改代码或 `.env` 后需 `systemctl restart`

启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hemu-fastapi
sudo systemctl status hemu-fastapi
sudo journalctl -u hemu-fastapi -f
```

常用命令：

```bash
sudo systemctl restart hemu-fastapi
sudo systemctl stop hemu-fastapi
```

## 探活

```bash
curl http://127.0.0.1:8600/health
# 期望统一业务外壳或健康响应（以实际接口为准）

# 有公网直连端口时：
curl http://你的公网IP:8600/health
curl http://你的公网IP:8600/docs
```

日志出现 `Application startup complete` 后再打开 `/docs`。若启动卡在播种或报数据库连接超时，先确认 Compose 中 Postgres 为 `healthy`，且 `DATABASE_URL` 正确。

## 下一步

- Nginx 与前端 → [04-nginx-frontend.md](./04-nginx-frontend.md)
- 验收清单 → [05-checklist.md](./05-checklist.md)
