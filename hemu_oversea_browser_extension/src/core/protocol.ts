import {
  ADMIN_PAGE_SOURCE,
  EXT_SOURCE,
  PROTOCOL_VERSION,
} from '../shared/config';

/** 平台级业务类型：安装检测等，不属于具体业务 Feature */
export const PLATFORM_BUSINESS = 'platform' as const;

export type BusinessType = typeof PLATFORM_BUSINESS | 'hotsell' | (string & {});

export type ExtAction =
  | 'PING'
  | 'PONG'
  | 'START'
  | 'STOP'
  | 'STATUS'
  | 'SYNC_CONFIRM'
  | 'ITEM_UPSERT'
  | 'ERROR';

/** 统一消息信封（管理端 page / content / background 共用） */
export interface ExtMessage<T = unknown> {
  source: typeof EXT_SOURCE | typeof ADMIN_PAGE_SOURCE;
  version: number;
  businessType: BusinessType;
  action: ExtAction;
  requestId: string;
  sessionId?: string;
  payload?: T;
  ts: number;
}

export interface PongPayload {
  extensionVersion: string;
  protocolVersion: number;
  supportedBusinessTypes: string[];
  /** 说明：安装检测为按需 PING，扩展不会全局主动上报 */
  detectMode: 'on_demand';
}

export function isAdminPageMessage(data: unknown): data is ExtMessage {
  if (!data || typeof data !== 'object') return false;
  const m = data as ExtMessage;
  return (
    m.source === ADMIN_PAGE_SOURCE &&
    typeof m.version === 'number' &&
    typeof m.businessType === 'string' &&
    typeof m.action === 'string' &&
    typeof m.requestId === 'string'
  );
}

export function isExtMessage(data: unknown): data is ExtMessage {
  if (!data || typeof data !== 'object') return false;
  const m = data as ExtMessage;
  return (
    m.source === EXT_SOURCE &&
    typeof m.version === 'number' &&
    typeof m.businessType === 'string' &&
    typeof m.action === 'string' &&
    typeof m.requestId === 'string'
  );
}

export function createExtMessage<T>(
  partial: Omit<ExtMessage<T>, 'source' | 'version' | 'ts'> & {
    version?: number;
    ts?: number;
  },
): ExtMessage<T> {
  return {
    source: EXT_SOURCE,
    version: partial.version ?? PROTOCOL_VERSION,
    businessType: partial.businessType,
    action: partial.action,
    requestId: partial.requestId,
    sessionId: partial.sessionId,
    payload: partial.payload,
    ts: partial.ts ?? Date.now(),
  };
}
