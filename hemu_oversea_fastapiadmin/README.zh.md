# hemu_oversea_fastapiadmin

[English](./README.md) | 简体中文

合木跨境系统管理端，基于 [Ant Design Pro](https://pro.ant.design/)（Umi Max 4、Ant Design 6、ProComponents）。

常见模块：供应商、店铺巡检与授权、商品与类目、人员、账号设置、敦煌网 OAuth 回调。接口经本地代理转发到 `hemu_oversea_fastapi`。

## 技术栈

- React 19 / TypeScript
- Umi Max 4 + Ant Design 6 + ProComponents
- Tailwind CSS v4 + antd-style
- Biome（检查与格式化）— 不使用 ESLint / Prettier
- Node.js 22+、npm（使用 `package-lock.json`）

## 环境要求

- Node.js 22+
- 可用的后端（本机 API 默认：`http://127.0.0.1:8600`）

## 安装

```powershell
cd hemu_oversea_fastapiadmin
npm install
```

## 开发

```powershell
# 带 mock 的开发服务（脚手架默认）
npm start

# 对接本机 / 指定环境代理（见 package.json 与 config/proxy.ts）
npm run dev
```

开发服务器默认：[http://localhost:8000](http://localhost:8000)。

`config/proxy.ts` 会把 `/api/` 转到后端。请把 `target` 与 Uvicorn 地址对齐（例如 `http://127.0.0.1:8600`）。

管理端登录：`/api/v1/admin/auth/login`，使用后端种子账号（`superadmin` + API `.env` 中的 `BOOTSTRAP_PASSWORD`），需图形验证码。

## 构建

```powershell
npm run build
```



## 常用脚本


| 脚本                | 说明                              |
| ----------------- | ------------------------------- |
| `npm start`       | 开发服务（默认带 mock）                  |
| `npm run dev`     | 无 mock / 按环境代理联调                |
| `npm run build`   | 生产构建（utoopack）                  |
| `npm run lint`    | Biome + TypeScript              |
| `npm run openapi` | 根据 OpenAPI 重新生成 `src/services/` |


请勿手改 `src/services/ant-design-pro/`，应使用 `npm run openapi` 重新生成。

`npm run simple` 不可逆；如需执行请先提交或建分支。

## 目录要点

```text
config/          # Umi 配置、路由、代理
src/
  pages/         # 业务页（可同目录放 service / mock / types）
  services/      # 生成与页面级 API 客户端
  access.ts      # 路由权限
  app.tsx        # 运行时配置与 getInitialState
```



## 不要提交

- `node_modules/`、`dist/`、`.umi/`
- 含密钥的本地环境文件（如有）

