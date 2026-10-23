import { defineConfig } from 'wxt';

/** 管理端注入范围：本地任意端口，以及 xiaohemu.net 的泛域名。 */
const adminMatches = ['http://localhost/*', 'https://*.xiaohemu.net/*'];

export default defineConfig({
  srcDir: '.',
  entrypointsDir: 'entrypoints',
  outDir: '.output',
  manifest: {
    name: '跨境Fast助手',
    description: 'HeMu admin companion extension (multi-business platform)',
    version: '0.1.0',
    host_permissions: [...adminMatches, '*://*.dhgate.com/*'],
  },
});
