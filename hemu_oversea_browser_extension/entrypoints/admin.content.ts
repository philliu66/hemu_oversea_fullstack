import { sendToBackground } from '../src/core/messaging';
import {
  createExtMessage,
  isAdminPageMessage,
  isExtMessage,
  type ExtMessage,
} from '../src/core/protocol';
import { ADMIN_PAGE_SOURCE, EXT_SOURCE, PROTOCOL_VERSION } from '../src/shared/config';

/**
 * 管理端桥：
 * - 页面 → background：业务 postMessage 转发
 * - background → 页面：把 SYNC_CONFIRM 等回传 postMessage 到页面
 *
 * 不在页面加载时主动 PING。
 */
export default defineContentScript({
  matches: ['http://localhost/*', 'http://127.0.0.1/*'],
  runAt: 'document_idle',
  main() {
    window.addEventListener('message', (event: MessageEvent) => {
      if (event.source !== window) return;
      if (!isAdminPageMessage(event.data)) return;
      if (event.data.version !== PROTOCOL_VERSION) {
        window.postMessage(
          createExtMessage({
            businessType: event.data.businessType,
            action: 'ERROR',
            requestId: event.data.requestId,
            payload: {
              error: 'protocol_version_mismatch',
              expected: PROTOCOL_VERSION,
              got: event.data.version,
            },
          }),
          window.location.origin,
        );
        return;
      }

      void handleFromPage(event.data);
    });

    // Background → 本 tab content → 页面（如 SYNC_CONFIRM）
    chrome.runtime.onMessage.addListener((raw, _sender, sendResponse) => {
      if (!isExtMessage(raw) || raw.source !== EXT_SOURCE) {
        return;
      }
      window.postMessage(raw, window.location.origin);
      sendResponse({ ok: true });
      return true;
    });
  },
});

async function handleFromPage(msg: ExtMessage): Promise<void> {
  try {
    const reply = await sendToBackground<ExtMessage>(msg);
    if (reply && reply.source === EXT_SOURCE) {
      window.postMessage(reply, window.location.origin);
    }
  } catch (err) {
    window.postMessage(
      createExtMessage({
        businessType: msg.businessType,
        action: 'ERROR',
        requestId: msg.requestId,
        sessionId: msg.sessionId,
        payload: {
          error: 'bridge_send_failed',
          message: err instanceof Error ? err.message : String(err),
        },
      }),
      window.location.origin,
    );
  }
}

void ADMIN_PAGE_SOURCE;
