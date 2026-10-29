import { request } from '@umijs/max';
import { AdminLogsApi } from '@/constants/api';
import type {
  ApiResponse,
  LoginLogPublic,
  OperationLogPublic,
  PageData,
} from '@/types/api';
import { unwrapApiData } from '@/utils/http';

type RequestOptions = {
  skipErrorHandler?: boolean;
  [key: string]: unknown;
};

function requireData<T>(payload: T | null, message: string): T {
  if (payload === null || payload === undefined) {
    throw new Error(message);
  }
  return payload;
}

export type LogListQuery = {
  keyword?: string;
  supplier_id?: number;
  time_from?: string;
  time_to?: string;
  page?: number;
  page_size?: number;
};

/** POST /api/v1/admin/logs/login/list */
export async function fetchLoginLogs(
  params: LogListQuery = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<LoginLogPublic>>>(
    AdminLogsApi.LOGIN_LIST,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        supplier_id: params.supplier_id,
        login_at_from: params.time_from,
        login_at_to: params.time_to,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<LoginLogPublic>>(res),
    '获取登录日志失败',
  );
}

/** POST /api/v1/admin/logs/operation/list */
export async function fetchOperationLogs(
  params: LogListQuery = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<OperationLogPublic>>>(
    AdminLogsApi.OPERATION_LIST,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        supplier_id: params.supplier_id,
        created_at_from: params.time_from,
        created_at_to: params.time_to,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<OperationLogPublic>>(res),
    '获取操作日志失败',
  );
}
