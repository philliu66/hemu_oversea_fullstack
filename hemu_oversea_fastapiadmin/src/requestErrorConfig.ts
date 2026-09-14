import type { RequestConfig } from '@umijs/max';
import { getIntl, history } from '@umijs/max';
import { message, notification } from 'antd';
import { isUnauthorizedCode } from '@/constants/errorCodes';
import type { ApiResponse } from '@/types/api';
import { clearTokens } from '@/utils/authToken';
import {
  applyRequestConvention,
  isApiResponse,
  isApiSuccess,
} from '@/utils/http';

const loginPath = '/user/login';

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

function t(id: string, defaultMessage: string, values?: Record<string, any>) {
  try {
    return getIntl().formatMessage({ id, defaultMessage }, values);
  } catch {
    return defaultMessage;
  }
}

function redirectToLogin() {
  clearTokens();
  if (typeof window === 'undefined') {
    return;
  }
  if (window.location.pathname === loginPath) {
    return;
  }
  const redirect = encodeURIComponent(
    window.location.pathname + window.location.search + window.location.hash,
  );
  history.replace(`${loginPath}?redirect=${redirect}`);
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

/**
 * 全局请求错误处理：
 * - 业务失败（code !== 0）：message.error 提示后端 message
 * - 未登录（40100 / HTTP 401）：先提示再跳转登录
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
      if (opts?.skipErrorHandler) {
        throw error;
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
          const tip = resolveApiErrorMessage(payload);
          if (isUnauthorizedCode(payload.code) || status === 401) {
            message.error(
              tip ||
                t('app.request.unauthorized', '未登录或登录已过期，请重新登录'),
            );
            redirectToLogin();
            return;
          }
          message.error(tip);
          return;
        }

        if (status === 401) {
          message.error(
            t('app.request.unauthorized', '未登录或登录已过期，请重新登录'),
          );
          redirectToLogin();
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
    (response) => {
      const payload = (response as { data?: unknown }).data;
      // Umi 仅在 data.success === false 时触发 errorThrower；
      // FastAPI 使用 code !== 0，需在此补抛错，统一走 errorHandler 弹提示。
      throwIfEnvelopeFailed(payload);
      return response;
    },
  ],
};
