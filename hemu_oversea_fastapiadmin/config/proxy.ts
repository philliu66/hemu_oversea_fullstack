/**
 * @name 开发代理（仅 max dev 生效，build 后无效）
 * @description 通过 UMI_ENV 切换后端：
 *   - local：本机 FastAPI（本机 Postgres）
 *   - dev：服务器 FastAPI（服务器 Postgres，经 Nginx HTTPS）
 * 前端页面部署在 /admin（见 src/constants/deploy.ts），/api 仍走域名根路径，代理规则无需改。
 * @doc https://umijs.org/docs/guides/proxy
 */
export default {
  /** 对接本机 uvicorn :8600 */
  local: {
    '/api/': {
      target: 'http://127.0.0.1:8600',
      changeOrigin: true,
    },
  },
  /** 对接服务器 https://hemuoversea.xiaohemu.net（浏览器仍请求本机 /api，由代理转发，免 CORS） */
  dev: {
    '/api/': {
      target: 'https://hemuoversea.xiaohemu.net',
      changeOrigin: true,
      secure: true,
    },
  },
  /** 兼容旧脚本 / record 等，默认等同 local */
  test: {
    '/api/': {
      target: 'http://127.0.0.1:8600',
      changeOrigin: true,
    },
  },
  pre: {
    '/api/': {
      target: 'http://127.0.0.1:8600',
      changeOrigin: true,
    },
  },
};
