import { bootstrapFeatures, routeMessage } from '../src/core/router';
import { isExtMessage, type ExtMessage } from '../src/core/protocol';
import { handleHotsellInternal } from '../src/features/hotsell/list-capture';
import { isHotsellInternalMessage } from '../src/features/hotsell/types';
import { ADMIN_PAGE_SOURCE, EXT_SOURCE } from '../src/shared/config';

export default defineBackground(() => {
  bootstrapFeatures();

  chrome.runtime.onMessage.addListener((raw, sender, sendResponse) => {
    // 敦煌页内部消息（非管理端信封）
    if (isHotsellInternalMessage(raw)) {
      void handleHotsellInternal(raw, sender)
        .then((reply) => sendResponse(reply))
        .catch((err: unknown) => {
          sendResponse({
            ok: false,
            message: err instanceof Error ? err.message : String(err),
          });
        });
      return true;
    }

    const msg = raw as ExtMessage;
    const fromAdminBridge =
      msg &&
      typeof msg === 'object' &&
      (msg.source === ADMIN_PAGE_SOURCE || msg.source === EXT_SOURCE);

    if (!fromAdminBridge || typeof msg.action !== 'string') {
      return;
    }

    void routeMessage(msg, sender)
      .then((reply) => {
        sendResponse(reply);
      })
      .catch((err: unknown) => {
        sendResponse({
          source: EXT_SOURCE,
          version: msg.version,
          businessType: msg.businessType,
          action: 'ERROR',
          requestId: msg.requestId,
          payload: {
            error: 'background_error',
            message: err instanceof Error ? err.message : String(err),
          },
          ts: Date.now(),
        } satisfies ExtMessage);
      });

    return true;
  });

  void isExtMessage;
});
