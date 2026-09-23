import { adminRefresh } from '@/services/admin/auth';
import { getRefreshToken } from '@/utils/authToken';

/** 并发 401 时只换发一次，其余请求等待同一结果 */
let refreshing: Promise<boolean> | null = null;

/**
 * 尝试用本地 refresh_token 换发新 token。
 * @returns 是否换发成功
 */
export function tryRefreshTokens(): Promise<boolean> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

async function doRefresh(): Promise<boolean> {
  if (!getRefreshToken()) {
    return false;
  }
  try {
    await adminRefresh();
    return true;
  } catch {
    return false;
  }
}

/** 仅供单测重置单飞状态 */
export function resetAuthRefreshState() {
  refreshing = null;
}
