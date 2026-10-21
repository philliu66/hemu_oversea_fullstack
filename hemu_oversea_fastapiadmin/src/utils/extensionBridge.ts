import {
  EXT_ADMIN_PAGE_SOURCE,
  EXT_PROTOCOL_VERSION,
  EXT_SOURCE,
} from '@/constants/extension';

export type ExtPageMessage = {
  source: typeof EXT_ADMIN_PAGE_SOURCE;
  version: number;
  businessType: string;
  action: string;
  requestId: string;
  sessionId?: string;
  payload?: unknown;
  ts: number;
};

export type ExtReplyMessage = {
  source: typeof EXT_SOURCE;
  version: number;
  businessType: string;
  action: string;
  requestId: string;
  sessionId?: string;
  payload?: unknown;
  ts: number;
};

function makeRequestId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function isExtReply(data: unknown, requestId: string): data is ExtReplyMessage {
  if (!data || typeof data !== 'object') return false;
  const m = data as ExtReplyMessage;
  return m.source === EXT_SOURCE && m.requestId === requestId;
}

/**
 * 向扩展发一条消息并等待同 requestId 的回复；超时则 resolve null。
 */
export function requestExtension(
  partial: {
    businessType: string;
    action: string;
    payload?: unknown;
    sessionId?: string;
  },
  timeoutMs = 2000,
): Promise<ExtReplyMessage | null> {
  const requestId = makeRequestId(partial.action.toLowerCase());
  const message: ExtPageMessage = {
    source: EXT_ADMIN_PAGE_SOURCE,
    version: EXT_PROTOCOL_VERSION,
    businessType: partial.businessType,
    action: partial.action,
    requestId,
    sessionId: partial.sessionId,
    payload: partial.payload,
    ts: Date.now(),
  };

  return new Promise((resolve) => {
    const timer = window.setTimeout(() => {
      window.removeEventListener('message', onMessage);
      resolve(null);
    }, timeoutMs);

    function onMessage(event: MessageEvent) {
      if (event.source !== window) return;
      if (!isExtReply(event.data, requestId)) return;
      window.clearTimeout(timer);
      window.removeEventListener('message', onMessage);
      resolve(event.data);
    }

    window.addEventListener('message', onMessage);
    window.postMessage(message, window.location.origin);
  });
}

/** 按需检测扩展是否安装（PING → PONG） */
export async function pingExtension(timeoutMs = 800): Promise<boolean> {
  const reply = await requestExtension(
    {
      businessType: 'platform',
      action: 'PING',
    },
    timeoutMs,
  );
  return !!reply && reply.action === 'PONG';
}

/**
 * 订阅扩展主动推送的消息（如 SYNC_CONFIRM）。
 * 返回取消订阅函数。
 */
export function subscribeExtensionMessages(
  handler: (msg: ExtReplyMessage) => void,
): () => void {
  const onMessage = (event: MessageEvent) => {
    if (event.source !== window) return;
    const data = event.data;
    if (!data || typeof data !== 'object') return;
    if ((data as ExtReplyMessage).source !== EXT_SOURCE) return;
    if (typeof (data as ExtReplyMessage).action !== 'string') return;
    handler(data as ExtReplyMessage);
  };
  window.addEventListener('message', onMessage);
  return () => window.removeEventListener('message', onMessage);
}
