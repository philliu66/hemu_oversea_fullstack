import { API_CHANNEL, API_SUCCESS_CODE, AUTH_WHITELIST } from '@/constants/api';
import type { ApiResponse } from '@/types/api';
import { getAccessToken } from './authToken';

export type RequestConventionConfig = {
  url?: string;
  method?: string;
  data?: unknown;
  headers?: Record<string, unknown>;
  /** 跳过自动附加公共 Header / Authorization */
  skipCommonHeaders?: boolean;
  [key: string]: unknown;
};

function normalizePath(url = ''): string {
  try {
    const pathname = url.includes('://')
      ? new URL(url).pathname
      : url.split('?')[0];
    return pathname.replace(/\/+$/, '') || '/';
  } catch {
    return url.split('?')[0]?.replace(/\/+$/, '') || '/';
  }
}

export function isAuthWhitelist(url?: string, method?: string): boolean {
  const path = normalizePath(url);
  const currentMethod = (method || 'GET').toUpperCase();
  return AUTH_WHITELIST.some(
    (item) => item.method === currentMethod && path.endsWith(item.path),
  );
}

export function isApiResponse(value: unknown): value is ApiResponse {
  return (
    !!value &&
    typeof value === 'object' &&
    'code' in value &&
    typeof (value as ApiResponse).code === 'number' &&
    'message' in value &&
    typeof (value as ApiResponse).message === 'string'
  );
}

export function isApiSuccess(res: ApiResponse): boolean {
  return res.code === API_SUCCESS_CODE;
}

/**
 * 构建公共上送 Header。
 * 后端目前只解析打日志、不校验签名；算法预留，后续可替换 buildSign。
 */
export function buildCommonHeaders(): Record<string, string> {
  const timestamp = String(Date.now());
  const channel = String(API_CHANNEL);
  return {
    'X-Timestamp': timestamp,
    'X-Channel': channel,
    'X-Sign': buildSign(timestamp, channel),
  };
}

/** 签名占位：后端启用校验后再换成正式算法 */
export function buildSign(timestamp: string, channel: string): string {
  return `${timestamp}.${channel}`;
}

/** 请求拦截：附加 X-Sign / X-Timestamp / X-Channel 与 Bearer Token */
export function applyRequestConvention<T extends RequestConventionConfig>(
  config: T,
): T {
  if (config.skipCommonHeaders) {
    return config;
  }

  const headers: Record<string, unknown> = {
    ...(config.headers as Record<string, unknown> | undefined),
    ...buildCommonHeaders(),
  };

  if (!isAuthWhitelist(config.url, config.method)) {
    const token = getAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  return {
    ...config,
    headers,
  };
}

/** 解开统一响应信封，兼容已直接返回业务 data 的情况 */
export function unwrapApiData<T>(res: unknown): T | null {
  if (isApiResponse(res)) {
    return (res.data as T | null) ?? null;
  }
  if (res === undefined || res === null) {
    return null;
  }
  return res as T;
}
