# 04 — Nginx 反代与前端对接

## 为什么要用 Nginx

- 对外只开 80/443，Uvicorn 不直接暴露公网
- 可同域托管管理端静态资源，简化 CORS
- 后续便于挂 HTTPS（证书）、限流、访问日志

## Nginx 反代示例（仅 API）

Uvicorn 监听 `127.0.0.1:8600` 时：

```nginx
server {
    listen 80;
    server_name 你的公网IP或域名;

    location /health {
        proxy_pass http://127.0.0.1:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

重载：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

安全组放行 80（及 443），可关闭对公网的 8600。

## 同域托管管理端静态资源（推荐）

管理端构建产物（如 `hemu_oversea_fastapiadmin/dist`）放到服务器某目录，例如 `/var/www/hemu-admin`：

```nginx
server {
    listen 80;
    server_name 你的公网IP或域名;
    root /var/www/hemu-admin;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SPA：未命中静态文件时回退到 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

此时前端生产配置可将 `baseURL` 保持为空字符串 `''`（相对路径请求同域 `/api/...`）。

## 前端工程需要改什么

管理端开发态：`config/proxy.ts` → `http://127.0.0.1:8600`，**仅本地有效**。

生产相关（`hemu_oversea_fastapiadmin`）：

| 位置 | 说明 |
|------|------|
| `src/app.tsx` 中 `request.baseURL` | 开发常为 `''`；跨域直连 API 时改为 `http://公网IP` 或 `http://公网IP:8600` |
| 构建命令 | 在管理端目录执行生产构建，再上传 `dist` |
| CORS | 若前后端不同源，服务器 `.env` 的 `CORS_ORIGINS` 必须包含前端页面的完整源 |

后端 `CORS_ORIGINS` 示例：

```env
# 同域 Nginx：前端源即 http://公网IP 或 https://域名
CORS_ORIGINS=["http://你的公网IP"]

# 前端仍在本机：额外加上本地源
CORS_ORIGINS=["http://localhost:8000","http://你的公网IP"]
```

## 敦煌 OAuth 回调

若启用敦煌授权，公网部署后必须同步修改 `.env` 中：

- `DHGATE_REDIRECT_URI`（后端回调，需公网可达）
- `DHGATE_FRONTEND_REDIRECT_URI`（前端落地页）

并在敦煌开放平台控制台把回调地址改成相同值。

## HTTPS（可选）

有域名后可用 Let’s Encrypt（certbot）或阿里云证书，在 Nginx 上配置 `443` 与跳转。HTTPS 后记得把 `CORS_ORIGINS`、OAuth 回调中的 `http` 改为 `https`。

## 下一步

- [05-checklist.md](./05-checklist.md)
