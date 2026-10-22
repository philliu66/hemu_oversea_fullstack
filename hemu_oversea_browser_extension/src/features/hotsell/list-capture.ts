import { createExtMessage, type ExtMessage } from '../../core/protocol';
import { bindAdminTab } from '../../core/session';
import { getHotsellJob, setHotsellJob, updateHotsellJob } from './job-store';
import {
  isHotsellInternalMessage,
  parseStartPayload,
  type HotsellCollectJob,
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
 * 在 background 用 host_permissions 直拉商品页 RSC 原文（不开新 tab、不做解析）。
 * 携带浏览器档案下 dhgate Cookie；走扩展网络栈（通常含系统/浏览器代理）。
 */
export async function fetchProductRscFlight(openUrl: string): Promise<{
  ok: boolean;
  error?: string;
  message?: string;
  openUrl: string;
  httpStatus?: number;
  contentType?: string;
  flightContent?: string;
  elapsedMs: number;
}> {
  const started = Date.now();
  try {
    const res = await fetch(openUrl, {
      method: 'GET',
      redirect: 'follow',
      credentials: 'include',
      headers: {
        RSC: '1',
        Accept: 'text/x-component',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    });
    const contentType = res.headers.get('content-type') || '';
    const flightContent = await res.text();
    const elapsedMs = Date.now() - started;

    if (!flightContent.trim()) {
      return {
        ok: false,
        error: 'empty_body',
        message: '商品页响应为空',
        openUrl,
        httpStatus: res.status,
        contentType,
        elapsedMs,
      };
    }

    return {
      ok: true,
      openUrl,
      httpStatus: res.status,
      contentType,
      flightContent,
      elapsedMs,
      message: '已获取 Flight 原文',
    };
  } catch (err) {
    return {
      ok: false,
      error: 'fetch_failed',
      message:
        err instanceof Error
          ? `拉取商品 RSC 失败: ${err.message}`
          : '拉取商品 RSC 失败',
      openUrl,
      elapsedMs: Date.now() - started,
    };
  }
}

/**
 * 管理端 START：
 * - list_collect：payload.collectConfig → 开标签监听
 * - fetch_product_rsc：payload.fillConfig + openUrl → background 直拉 Flight，同步回传（不占 job、不开 tab）
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
        '热卖配置无效：list_collect 需 collectConfig；fetch_product_rsc 需 openUrl（及 fillConfig）',
    };
  }

  if (config.mode === 'fetch_product_rsc') {
    if (!isHttpUrl(config.openUrl)) {
      return {
        ok: false,
        error: 'invalid_config',
        message: 'fetch_product_rsc 配置无效：需要合法的商品 openUrl',
      };
    }
    // 不触碰进行中的 list_collect Job；同步拉 Flight 后随 START 回复返回
    const result = await fetchProductRscFlight(config.openUrl);
    return {
      ...result,
      phase: 'B',
      mode: 'fetch_product_rsc' as const,
      fillConfig: config.fillConfig,
    };
  }

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

  const session = bindAdminTab(adminTabId, 'hotsell', msg.sessionId);

  // 开启新列表采集前关掉上一次采集页（保留会话，仅换页）
  const prev = getHotsellJob();
  if (prev?.captureTabId) {
    try {
      await chrome.tabs.remove(prev.captureTabId);
    } catch {
      // 可能已关闭
    }
  }

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

  const tab = await chrome.tabs.create({
    url: config.collectConfig.openUrl,
    active: true,
  });
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
    mode: 'list_collect' as const,
    sessionId: session.sessionId,
    captureTabId: tab.id,
    message: '已打开采集页并开始监听',
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
  action: 'SYNC_CONFIRM',
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

/** 处理敦煌页 content 发来的内部消息（仅 list_collect） */
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
      watchApiUrl: job.watchApiUrl,
      hitCount: job.hitCount,
      hasLatest: job.latestData != null,
    };
  }

  if (!current || current.status !== 'active') {
    return { ok: false, message: '无进行中的采集任务' };
  }

  if (raw.op === 'API_HIT') {
    const next = updateHotsellJob({
      hitCount: current.hitCount + 1,
      latestData: raw.data,
    });
    return {
      ok: true,
      hitCount: next?.hitCount ?? 0,
      hasLatest: true,
    };
  }

  if (raw.op === 'CONFIRM') {
    const adminTabId = current.adminTabId;
    const captureTabId = current.captureTabId;

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
