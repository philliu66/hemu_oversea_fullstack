import { defineConfig } from 'wxt';

/**
 * 管理端 origin 白名单：仅这些页面会注入 admin content script（桥）。
 * 扩展不会在页面加载时主动检测；只有页面发 PING 才响应。
 */
// 省略端口 = 匹配该 host 任意端口（Chrome match pattern）
const adminMatches = [
  'http://localhost/*',
  'http://127.0.0.1/*',
  // 按环境追加生产管理端域名，例如：
  // 'https://admin.example.com/*',
];

export default defineConfig({
  srcDir: '.',
  entrypointsDir: 'entrypoints',
  outDir: '.output',
  manifest: {
    name: 'HeMu Browser Extension',
    description: 'HeMu admin companion extension (multi-business platform)',
    version: '0.1.0',
    permissions: ['storage', 'tabs'],
    host_permissions: [
      ...adminMatches,
      '*://*.dhgate.com/*',
    ],
  },
});
