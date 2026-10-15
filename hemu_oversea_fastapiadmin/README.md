# hemu_oversea_fastapiadmin

English | [简体中文](./README.zh.md)

Admin console for HeMu Oversea, built on [Ant Design Pro](https://pro.ant.design/) (Umi Max 4, Ant Design 6, ProComponents).

Typical modules: suppliers, shop inspection & authorization, products & categories, staff, account settings, and DHgate OAuth callback. API calls go through the local proxy to `hemu_oversea_fastapi`.

## Stack

- React 19 / TypeScript
- Umi Max 4 + Ant Design 6 + ProComponents
- Tailwind CSS v4 + antd-style
- Biome (lint/format) — no ESLint/Prettier
- Node.js 22+, npm (`package-lock.json`)

## Requirements

- Node.js 22+
- Running backend (default local API: `http://127.0.0.1:8600`)

## Setup

```powershell
cd hemu_oversea_fastapiadmin
npm install
```

## Development

```powershell
# Full app with mock (template default)
npm start

# Against local / env-specific proxy (see package.json & config/proxy.ts)
npm run dev
```

Dev server defaults to [http://localhost:8000](http://localhost:8000).

`config/proxy.ts` forwards `/api/` to the backend. Keep `target` aligned with Uvicorn (e.g. `http://127.0.0.1:8600`).

Admin login: `/api/v1/admin/auth/login` with the backend bootstrap account (`superadmin` + `BOOTSTRAP_PASSWORD` from the API `.env`). Captcha is required.

## Build

```powershell
npm run build
```

## Useful scripts

| Script            | Purpose                                      |
| ----------------- | -------------------------------------------- |
| `npm start`       | Dev server (with mock by default)            |
| `npm run dev`     | Dev without mock / env-specific proxy        |
| `npm run build`   | Production build (utoopack)                  |
| `npm run lint`    | Biome + TypeScript                           |
| `npm run openapi` | Regenerate `src/services/` from OpenAPI      |

Do **not** hand-edit `src/services/ant-design-pro/` — regenerate with `npm run openapi`.

`npm run simple` is irreversible; commit or branch first if you ever need it.

## Project layout (highlights)

```text
config/          # Umi config, routes, proxy
src/
  pages/         # Feature pages (co-located service / mock / types)
  services/      # Generated & page-level API clients
  access.ts      # Route access
  app.tsx        # Runtime config & getInitialState
```

## Do not commit

- `node_modules/`, `dist/`, `.umi/`
- Local env files with secrets (if any)
