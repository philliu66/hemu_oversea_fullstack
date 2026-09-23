import { request } from '@umijs/max';
import { AdminUserApi } from '@/constants/api';
import type { ApiResponse, SupplierUserOption } from '@/types/api';
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

/** GET /api/v1/admin/users/supplier-list */
export async function fetchSupplierUserOptions(
  params: { keyword?: string; supplier_id?: number } = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SupplierUserOption[]>>(
    AdminUserApi.SUPPLIER_LIST,
    {
      method: 'GET',
      params: {
        keyword: params.keyword,
        supplier_id: params.supplier_id,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<SupplierUserOption[]>(res),
    '获取供应商用户失败',
  );
}
