import { createExtMessage, type ExtMessage } from '../../core/protocol';
import { bindAdminTab } from '../../core/session';
import { getHotsellJob, setHotsellJob, updateHotsellJob } from './job-store';
import {
  isHotsellInternalMessage,
  parseStartPayload,
  type HotsellCollectJob,
  type HotsellFillJob,
  type HotsellInternalMessage,
} from './types';

function isHttpUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

async function finishAndCloseCapture(
  adminTabId: number,
  captureTabId?: number,
): Promise<void> {
  setHotsellJob(null);
  try {
    await chrome.tabs.update(adminTabId, { active: true });
  } catch {
    // ignore
  }
  if (captureTabId) {
    try {
      await chrome.tabs.remove(captureTabId);
    } catch {
      // ignore
    }
  }
}

/**
 * 管理端 START：
 * - list_collect：payload.collectConfig
 * - detail_fill：payload.fillConfig + openUrl
 *
 * 用判别联合写入对应 Job 形态，不与另一模式的字段混写。
 */
export async function startHotsellJob(
  msg: ExtMessage,
  sender: chrome.runtime.MessageSender,
): Promise<unknown> {
  const adminTabId = sender.tab?.id;
  if (!adminTabId) {
    return {
      ok: false,
      error: 'missing_admin_tab',
      message: '无法识别管理端标签页，请在管理端页面发起',
    };
  }

  const config = parseStartPayload(msg.payload);
  if (!config) {
    return {
      ok: false,
      error: 'invalid_config',
      message:
        '热卖配置无效：list_collect 需 collectConfig；detail_fill 需 fillConfig + openUrl',
    };
  }

  if (config.mode === 'list_collect') {
    if (
      !isHttpUrl(config.collectConfig.openUrl) ||
      !isHttpUrl(config.collectConfig.watchApiUrl)
    ) {
      return {
        ok: false,
        error: 'invalid_config',
        message: '列表采集配置无效：需要合法的 openUrl / watchApiUrl',
      };
    }
  } else if (!isHttpUrl(config.openUrl)) {
    return {
      ok: false,
      error: 'invalid_config',
      message: '单次补充配置无效：需要合法的商品 openUrl',
    };
  }

  const session = bindAdminTab(adminTabId, 'hotsell', msg.sessionId);

  // 开启新任务前关掉上一次采集/补充页（保留会话，仅换页，不先清空再写）
  const prev = getHotsellJob();
  if (prev?.captureTabId) {
    try {
      await chrome.tabs.remove(prev.captureTabId);
    } catch {
      // 可能已关闭
    }
  }

  const openUrl =
    config.mode === 'list_collect'
      ? config.collectConfig.openUrl
      : config.openUrl;

  // 先按模式写入完整 Job，再开页，避免 PAGE_READY 抢跑读到半旧状态
  if (config.mode === 'list_collect') {
    const next: HotsellCollectJob = {
      mode: 'list_collect',
      sessionId: session.sessionId,
      adminTabId,
      captureTabId: undefined,
      openUrl: config.collectConfig.openUrl,
      watchApiUrl: config.collectConfig.watchApiUrl,
      alertTip:
        config.collectConfig.alertTip ||
        '请在本页完成热卖数据采集操作',
      hitCount: 0,
      latestData: null,
      status: 'active',
      createdAt: Date.now(),
    };
    setHotsellJob(next);
  } else {
    const next: HotsellFillJob = {
      mode: 'detail_fill',
      sessionId: session.sessionId,
      adminTabId,
      captureTabId: undefined,
      openUrl: config.openUrl,
      alertTip:
        (typeof config.fillConfig.alertTip === 'string' &&
          config.fillConfig.alertTip.trim()) ||
        (typeof config.fillConfig.popTip === 'string' &&
          config.fillConfig.popTip.trim()) ||
        '请在本页完成热卖品详情补充',
      fillConfig: config.fillConfig,
      status: 'active',
      createdAt: Date.now(),
    };
    setHotsellJob(next);
  }

  const tab = await chrome.tabs.create({ url: openUrl, active: true });
  if (!tab.id) {
    setHotsellJob(null);
    return {
      ok: false,
      error: 'open_tab_failed',
      message: '打开目标页失败',
    };
  }

  updateHotsellJob({ captureTabId: tab.id });

  return {
    ok: true,
    phase: 'B',
    mode: config.mode,
    sessionId: session.sessionId,
    captureTabId: tab.id,
    message:
      config.mode === 'detail_fill'
        ? '已打开商品页，可进行单次补充'
        : '已打开采集页并开始监听',
  };
}

/** @deprecated 使用 startHotsellJob */
export const startListCapture = startHotsellJob;

export async function stopListCapture(): Promise<unknown> {
  const current = getHotsellJob();
  if (!current) {
    return { ok: true, message: '无进行中的采集任务' };
  }
  await finishAndCloseCapture(current.adminTabId, current.captureTabId);
  return { ok: true, message: '已取消' };
}

async function relaySyncToAdmin(
  action: 'SYNC_CONFIRM' | 'FILL_CONFIRM',
  data: unknown,
): Promise<{ ok: boolean; message?: string }> {
  const current = getHotsellJob();
  if (!current) {
    return { ok: false, message: '采集会话已结束' };
  }

  const reply = createExtMessage({
    businessType: 'hotsell',
    action,
    requestId: `sync_${Date.now()}`,
    sessionId: current.sessionId,
    payload: data,
  });

  try {
    await chrome.tabs.sendMessage(current.adminTabId, reply);
    return { ok: true, message: '已回传管理端' };
  } catch (err) {
    return {
      ok: false,
      message:
        err instanceof Error
          ? `回传管理端失败: ${err.message}`
          : '回传管理端失败（管理端页可能已关闭）',
    };
  }
}

/** 处理敦煌页 content 发来的内部消息 */
export async function handleHotsellInternal(
  raw: HotsellInternalMessage,
  sender: chrome.runtime.MessageSender,
): Promise<unknown> {
  if (!isHotsellInternalMessage(raw)) {
    return { ok: false, message: 'invalid_internal_message' };
  }

  const current = getHotsellJob();

  if (raw.op === 'PAGE_READY') {
    if (!current || current.status !== 'active') {
      return { ok: false, active: false };
    }
    const tabId = sender.tab?.id;
    if (tabId && (!current.captureTabId || current.captureTabId === tabId)) {
      updateHotsellJob({ captureTabId: tabId });
    } else if (tabId && current.captureTabId && current.captureTabId !== tabId) {
      return { ok: false, active: false };
    }
    const job = getHotsellJob()!;
    return {
      ok: true,
      active: true,
      mode: job.mode,
      alertTip: job.alertTip,
      watchApiUrl:
        job.mode === 'list_collect' ? job.watchApiUrl : undefined,
      hitCount: job.mode === 'list_collect' ? job.hitCount : 0,
      hasLatest: job.mode === 'list_collect' ? job.latestData != null : false,
    };
  }

  if (!current || current.status !== 'active') {
    return { ok: false, message: '无进行中的采集任务' };
  }

  if (raw.op === 'API_HIT') {
    if (current.mode !== 'list_collect') {
      return { ok: false, message: '当前模式不监听列表接口' };
    }
    const next = updateHotsellJob({
      hitCount: current.hitCount + 1,
      latestData: raw.data,
    });
    const collect = next?.mode === 'list_collect' ? next : null;
    return {
      ok: true,
      hitCount: collect?.hitCount ?? 0,
      hasLatest: true,
    };
  }

  if (raw.op === 'CONFIRM') {
    const adminTabId = current.adminTabId;
    const captureTabId = current.captureTabId;

    if (current.mode === 'detail_fill') {
      await finishAndCloseCapture(adminTabId, captureTabId);
      return {
        ok: true,
        message: '补充流程占位结束（业务逻辑待接入）',
        reserved: true,
      };
    }

    if (current.latestData == null) {
      return { ok: false, message: '尚未监听到接口数据，请先在本页触发列表加载' };
    }
    const result = await relaySyncToAdmin('SYNC_CONFIRM', current.latestData);
    if (result.ok) {
      await finishAndCloseCapture(adminTabId, captureTabId);
    }
    return result;
  }

  if (raw.op === 'CANCEL') {
    const adminTabId = current.adminTabId;
    try {
      await chrome.tabs.update(adminTabId, { active: true });
    } catch {
      // ignore
    }
    return stopListCapture();
  }

  return { ok: false, message: 'unknown_op' };
}
