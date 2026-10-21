/**
 * 热卖业务模式：
 * - list_collect：列表采集（部分信息，对应 collectConfig）
 * - detail_fill：单次补充详情（对应 fillConfig + 商品 openUrl）
 *
 * START 用嵌套配置 + mode 判别，避免 collect/fill 同名字段（如 alertTip）扁平合并后串扰。
 */
export type HotsellJobMode = 'list_collect' | 'detail_fill';

/** 列表采集配置（与系统配置 collectConfig 对齐） */
export type HotsellCollectConfig = {
  openUrl: string;
  watchApiUrl: string;
  alertTip?: string;
};

/** 单次补充配置（与系统配置 fillConfig 对齐） */
export type HotsellFillConfig = {
  /** 商品页顶部提示 */
  alertTip?: string;
  /** 兼容旧字段名 */
  popTip?: string;
  [key: string]: unknown;
};

/** 列表采集 START payload */
export type HotsellCollectPayload = {
  mode: 'list_collect';
  collectConfig: HotsellCollectConfig;
};

/** 单次补充 START payload */
export type HotsellFillPayload = {
  mode: 'detail_fill';
  /** 当前商品链接（覆盖/补充 fillConfig 内可能没有的 openUrl） */
  openUrl: string;
  fillConfig: HotsellFillConfig;
};

export type HotsellStartPayload = HotsellCollectPayload | HotsellFillPayload;

/** 列表采集进行中的任务 */
export type HotsellCollectJob = {
  mode: 'list_collect';
  sessionId: string;
  adminTabId: number;
  captureTabId?: number;
  openUrl: string;
  watchApiUrl: string;
  /** 仅来自 collectConfig.alertTip */
  alertTip: string;
  hitCount: number;
  latestData: unknown | null;
  status: 'active' | 'stopped';
  createdAt: number;
};

/** 单次补充进行中的任务 */
export type HotsellFillJob = {
  mode: 'detail_fill';
  sessionId: string;
  adminTabId: number;
  captureTabId?: number;
  openUrl: string;
  /** 仅来自 fillConfig.alertTip / popTip */
  alertTip: string;
  fillConfig: HotsellFillConfig;
  status: 'active' | 'stopped';
  createdAt: number;
};

export type HotsellJob = HotsellCollectJob | HotsellFillJob;

/** 敦煌 content ↔ background 内部消息 */
export type HotsellInternalMessage =
  | { channel: 'hotsell'; op: 'PAGE_READY' }
  | { channel: 'hotsell'; op: 'API_HIT'; data: unknown; url: string }
  | { channel: 'hotsell'; op: 'CONFIRM' }
  | { channel: 'hotsell'; op: 'CANCEL' };

export function isHotsellInternalMessage(raw: unknown): raw is HotsellInternalMessage {
  if (!raw || typeof raw !== 'object') return false;
  const m = raw as HotsellInternalMessage;
  return m.channel === 'hotsell' && typeof m.op === 'string';
}

function readStr(o: Record<string, unknown>, key: string): string {
  const v = o[key];
  return typeof v === 'string' ? v.trim() : '';
}

function asRecord(v: unknown): Record<string, unknown> | null {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return null;
  return v as Record<string, unknown>;
}

function resolveCollectAlertTip(c: Record<string, unknown>): string {
  return (
    readStr(c, 'alertTip') || '请在本页完成热卖数据采集操作'
  );
}

function resolveFillAlertTip(c: Record<string, unknown>): string {
  return (
    readStr(c, 'alertTip') ||
    readStr(c, 'popTip') ||
    '请在本页完成热卖品详情补充'
  );
}

/**
 * 解析管理端 START payload。
 * 仅认嵌套 collectConfig / fillConfig；不再接受扁平同名字段，避免模式间串扰。
 */
export function parseStartPayload(payload: unknown): HotsellStartPayload | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return null;
  }
  const o = payload as Record<string, unknown>;
  const mode = o.mode === 'detail_fill' ? 'detail_fill' : 'list_collect';

  if (mode === 'detail_fill') {
    const fillConfig = asRecord(o.fillConfig);
    if (!fillConfig) return null;
    const openUrl = readStr(o, 'openUrl') || readStr(fillConfig, 'openUrl');
    if (!openUrl) return null;
    return {
      mode: 'detail_fill',
      openUrl,
      fillConfig: {
        ...fillConfig,
        alertTip: resolveFillAlertTip(fillConfig),
      },
    };
  }

  const collectConfig = asRecord(o.collectConfig);
  if (!collectConfig) return null;
  const openUrl = readStr(collectConfig, 'openUrl');
  const watchApiUrl = readStr(collectConfig, 'watchApiUrl');
  if (!openUrl || !watchApiUrl) return null;
  return {
    mode: 'list_collect',
    collectConfig: {
      openUrl,
      watchApiUrl,
      alertTip: resolveCollectAlertTip(collectConfig),
    },
  };
}
