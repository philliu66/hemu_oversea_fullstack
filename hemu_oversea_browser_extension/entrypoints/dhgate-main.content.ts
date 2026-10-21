import {
  HOOK_INSTALL_SOURCE,
  HOOK_SOURCE,
  installNetHookInMainWorld,
} from '../src/sites/dhgate/net-hook';

/**
 * 敦煌页 MAIN world：不受页面 CSP 对「扩展内联 script」的限制，
 * 在尽可能早的时机劫持 fetch / XHR。
 */
export default defineContentScript({
  matches: ['*://*.dhgate.com/*'],
  world: 'MAIN',
  runAt: 'document_start',
  main() {
    window.addEventListener('message', (event: MessageEvent) => {
      if (event.source !== window) return;
      const data = event.data;
      if (!data || data.source !== HOOK_INSTALL_SOURCE) return;
      if (data.op === 'INSTALL' && typeof data.watchApiUrl === 'string') {
        installNetHookInMainWorld(data.watchApiUrl);
      }
    });

    // 告知 isolated：MAIN 已就绪（便于重发 INSTALL）
    try {
      window.postMessage({ source: HOOK_SOURCE, op: 'MAIN_READY', ts: Date.now() }, '*');
    } catch {
      // ignore
    }
  },
});
