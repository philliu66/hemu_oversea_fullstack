/**
 * @name 代理的配置
 * @see 在生产环境 代理是无法生效的，所以这里没有生产环境的配置
 * @doc https://umijs.org/docs/guides/proxy
 */
export default {
  /** 本地联调 FastAPI：http://127.0.0.1:8600（避免与管理端开发端口 8000 冲突） */
  dev: {
    '/api/': {
      target: 'http://127.0.0.1:8600',
      changeOrigin: true,
    },
  },
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
