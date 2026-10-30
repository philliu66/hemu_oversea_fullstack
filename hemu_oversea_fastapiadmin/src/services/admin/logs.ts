import { request } from '@umijs/max';
import { AdminLogsApi } from '@/constants/api';
import type {
  ApiResponse,
  LoginActivitySummary,
  LoginActivityTimeline,
  LoginActivityUserOption,
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

/** POST /api/v1/admin/logs/login/activity/users */
export async function fetchLoginActivityUsers(supplierId?: number) {
  const res = await request<ApiResponse<LoginActivityUserOption[]>>(
    AdminLogsApi.LOGIN_ACTIVITY_USERS,
    {
      method: 'POST',
      data: { supplier_id: supplierId },
    },
  );
  return requireData(
    unwrapApiData<LoginActivityUserOption[]>(res),
    '获取用户列表失败',
  );
}

/** POST /api/v1/admin/logs/login/activity/summary */
export async function fetchLoginActivitySummary(params: {
  user_id: number;
  supplier_id?: number;
  time_from: string;
  time_to: string;
}) {
  const res = await request<ApiResponse<LoginActivitySummary>>(
    AdminLogsApi.LOGIN_ACTIVITY_SUMMARY,
    { method: 'POST', data: params },
  );
  return requireData(
    unwrapApiData<LoginActivitySummary>(res),
    '获取活跃时长失败',
  );
}

/** POST /api/v1/admin/logs/login/activity/timeline */
export async function fetchLoginActivityTimeline(params: {
  user_id: number;
  supplier_id?: number;
  time_from: string;
  time_to: string;
}) {
  const res = await request<ApiResponse<LoginActivityTimeline>>(
    AdminLogsApi.LOGIN_ACTIVITY_TIMELINE,
    { method: 'POST', data: params },
  );
  return requireData(
    unwrapApiData<LoginActivityTimeline>(res),
    '获取活跃时段失败',
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
