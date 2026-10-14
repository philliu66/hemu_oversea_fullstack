import type { AxiosResponse, RequestConfig } from '@umijs/max';
import { history, request } from '@umijs/max';
import { message, notification } from 'antd';
import { APP_LOGIN_PATH, isAppRoutePath, stripAppBase } from '@/constants/deploy';
import { isUnauthorizedCode } from '@/constants/errorCodes';
import type { ApiResponse } from '@/types/api';
import { tryRefreshTokens } from '@/utils/authRefresh';
import { clearTokens } from '@/utils/authToken';
import {
  applyRequestConvention,
  isApiResponse,
  isApiSuccess,
  isAuthWhitelist,
} from '@/utils/http';

/** 换发成功后重试原请求时打标，避免死循环 */
const RETRY_AFTER_REFRESH = '__isRetryAfterRefresh';

enum ErrorShowType {
  SILENT = 0,
  WARN_MESSAGE = 1,
  ERROR_MESSAGE = 2,
  NOTIFICATION = 3,
  REDIRECT = 9,
}

interface ResponseStructure {
  success?: boolean;
  data: unknown;
  errorCode?: number | string;
  errorMessage?: string;
  showType?: ErrorShowType;
}

type RequestOpts = {
  url?: string;
  method?: string;
  skipErrorHandler?: boolean;
  /** 跳过 401 静默换发（如 refresh 自身） */
  skipAuthRefresh?: boolean;
  [key: string]: unknown;
};

function interpolateMessage(
  template: string,
  values?: Record<string, unknown>,
): string {
  if (!values) {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = values[key];
    if (value === undefined || value === null) {
      return `{${key}}`;
    }
    return String(value);
  });
}

function t(_id: string, defaultMessage: string, values?: Record<string, unknown>) {
  return interpolateMessage(defaultMessage, values);
}

function redirectToLogin() {
  clearTokens();
  if (typeof window === 'undefined') {
    return;
  }
  if (isAppRoutePath(window.location.pathname, APP_LOGIN_PATH)) {
    return;
  }
  // redirect 存 Umi 路由路径（不含 APP_BASE），与 getInitialState 一致
  const routePath = stripAppBase(window.location.pathname);
  const redirect = encodeURIComponent(
    routePath + window.location.search + window.location.hash,
  );
  history.replace(`${APP_LOGIN_PATH}?redirect=${redirect}`);
}

function throwBizError(payload: {
  errorCode?: number | string;
  errorMessage?: string;
  showType?: ErrorShowType;
  data?: unknown;
}) {
  const error: any = new Error(payload.errorMessage);
  error.name = 'BizError';
  error.info = payload;
  throw error;
}

/** 从校验失败 data.errors 拼一条可读提示 */
function formatValidationDetail(data: unknown): string {
  if (!data || typeof data !== 'object') {
    return '';
  }
  const errors = (data as { errors?: unknown }).errors;
  if (!Array.isArray(errors) || errors.length === 0) {
    return '';
  }
  const first = errors[0] as { field?: string; message?: string };
  if (!first?.message) {
    return '';
  }
  return first.field ? `${first.field}: ${first.message}` : first.message;
}

/** 优先取后端 message，必要时附带校验明细 */
function resolveApiErrorMessage(payload: ApiResponse): string {
  const detail = formatValidationDetail(payload.data);
  if (payload.message && detail) {
    return `${payload.message}（${detail}）`;
  }
  return (
    payload.message ||
    t('app.request.failed', '请求失败，请重试。')
  );
}

/** FastAPI 信封 code !== 0 时抛业务错误 */
function throwIfEnvelopeFailed(payload: unknown) {
  if (!isApiResponse(payload) || isApiSuccess(payload)) {
    return;
  }
  const unauthorized = isUnauthorizedCode(payload.code);
  throwBizError({
    errorCode: payload.code,
    errorMessage: resolveApiErrorMessage(payload),
    showType: unauthorized
      ? ErrorShowType.REDIRECT
      : ErrorShowType.ERROR_MESSAGE,
    data: payload.data,
  });
}

function isUnauthorizedError(error: any): boolean {
  if (error?.name === 'BizError') {
    return isUnauthorizedCode(Number(error.info?.errorCode));
  }
  if (error?.response) {
    const status = error.response.status as number;
    const payload = error.response.data;
    if (isApiResponse(payload) && isUnauthorizedCode(payload.code)) {
      return true;
    }
    return status === 401;
  }
  return false;
}

function isUnauthorizedPayload(payload: unknown): boolean {
  return isApiResponse(payload) && isUnauthorizedCode(payload.code);
}

function canAttemptRefresh(opts: RequestOpts): boolean {
  if (opts.skipAuthRefresh || opts[RETRY_AFTER_REFRESH]) {
    return false;
  }
  if (isAuthWhitelist(opts.url, opts.method)) {
    return false;
  }
  return true;
}

function unauthorizedTip(error: any): string {
  if (error?.name === 'BizError' && error.info?.errorMessage) {
    return error.info.errorMessage;
  }
  const payload = error?.response?.data;
  if (isApiResponse(payload)) {
    return resolveApiErrorMessage(payload);
  }
  return t('app.request.unauthorized', '未登录或登录已过期，请重新登录');
}

/**
 * access 过期时静默换发并重试原请求。
 *
 * 必须放在 axios response 拦截器里完成：umi 生成的 request 在 catch 里会
 * 忽略 errorHandler 的返回值并始终 reject(原错误)，导致「第一次失败、
 * 第二次才成功」。拦截器返回 AxiosResponse 才能让原 Promise resolve。
 */
async function refreshAndRetry(
  config: Record<string, unknown> | undefined,
): Promise<AxiosResponse | null> {
  if (!config || typeof config.url !== 'string' || !config.url) {
    return null;
  }
  const opts: RequestOpts = {
    url: config.url,
    method: typeof config.method === 'string' ? config.method : 'GET',
    skipAuthRefresh: Boolean(config.skipAuthRefresh),
    [RETRY_AFTER_REFRESH]: Boolean(config[RETRY_AFTER_REFRESH]),
  };
  if (!canAttemptRefresh(opts)) {
    return null;
  }

  const refreshed = await tryRefreshTokens();
  if (!refreshed) {
    return null;
  }

  const headers = {
    ...((config.headers as Record<string, unknown> | undefined) || {}),
  };
  delete headers.Authorization;
  delete headers.authorization;

  // getResponse: true → 返回 AxiosResponse，供拦截器恢复原请求
  return request(config.url, {
    ...config,
    headers,
    getResponse: true,
    [RETRY_AFTER_REFRESH]: true,
  });
}

/**
 * 全局请求错误处理：
 * - 业务失败（code !== 0）：message.error 提示后端 message
 * - 未登录（40100 / HTTP 401）：换发在 response 拦截器；此处仅提示并跳登录
 * - 网络异常：统一兜底文案
 */
export const errorConfig: RequestConfig = {
  errorConfig: {
    errorThrower: (res) => {
      throwIfEnvelopeFailed(res);

      const { success, data, errorCode, errorMessage, showType } =
        res as unknown as ResponseStructure;
      if (success === false) {
        throwBizError({ errorCode, errorMessage, showType, data });
      }
    },
    errorHandler: (error: any, opts: any) => {
      const requestOpts = (opts || {}) as RequestOpts;

      if (requestOpts.skipErrorHandler) {
        throw error;
      }

      // 换发/重试已在 response 拦截器完成；走到这里说明无法续期
      if (isUnauthorizedError(error)) {
        message.error(unauthorizedTip(error));
        redirectToLogin();
        return;
      }

      // 业务错误（响应拦截器 / errorThrower 抛出）
      if (error.name === 'BizError') {
        const errorInfo: ResponseStructure | undefined = error.info;
        if (!errorInfo) {
          message.error(t('app.request.failed', '请求失败，请重试。'));
          return;
        }
        const { errorMessage, errorCode } = errorInfo;
        switch (errorInfo.showType) {
          case ErrorShowType.SILENT:
            break;
          case ErrorShowType.WARN_MESSAGE:
            message.warning(errorMessage);
            break;
          case ErrorShowType.ERROR_MESSAGE:
            message.error(
              errorMessage || t('app.request.failed', '请求失败，请重试。'),
            );
            break;
          case ErrorShowType.NOTIFICATION:
            notification.open({
              title: errorCode,
              description: errorMessage,
            });
            break;
          case ErrorShowType.REDIRECT:
            message.error(
              errorMessage ||
                t('app.request.unauthorized', '未登录或登录已过期，请重新登录'),
            );
            redirectToLogin();
            break;
          default:
            message.error(
              errorMessage || t('app.request.failed', '请求失败，请重试。'),
            );
        }
        return;
      }

      // HTTP 层错误（4xx / 5xx）
      if (error.response) {
        const status = error.response.status as number;
        const payload = error.response.data;

        if (isApiResponse(payload) && !isApiSuccess(payload)) {
          message.error(resolveApiErrorMessage(payload));
          return;
        }

        message.error(
          t('app.request.statusError', '请求失败（{status}）', { status }),
        );
        return;
      }

      if (typeof navigator !== 'undefined' && !navigator.onLine) {
        message.error(
          t('app.request.offline', '网络不可用，请检查网络连接后重试。'),
        );
        return;
      }

      if (error.request) {
        message.error(t('app.request.noResponse', '服务器无响应，请重试。'));
        return;
      }

      message.error(t('app.request.failed', '请求失败，请重试。'));
    },
  },

  requestInterceptors: [(config) => applyRequestConvention(config)],

  responseInterceptors: [
    [
      async (response) => {
        const payload = (response as { data?: unknown }).data;
        // HTTP 200 但业务码 40100：同样尝试静默换发后重试
        if (isUnauthorizedPayload(payload)) {
          const retried = await refreshAndRetry(
            (response as { config?: Record<string, unknown> }).config,
          );
          if (retried) {
            return retried;
          }
        }
        // Umi 仅在 data.success === false 时触发 errorThrower；
        // FastAPI 使用 code !== 0，需在此补抛错，统一走 errorHandler 弹提示。
        throwIfEnvelopeFailed(payload);
        return response;
      },
      async (error: any) => {
        if (isUnauthorizedError(error)) {
          const retried = await refreshAndRetry(
            error?.config as Record<string, unknown> | undefined,
          );
          if (retried) {
            return retried;
          }
        }
        return Promise.reject(error);
      },
    ],
  ],
};
