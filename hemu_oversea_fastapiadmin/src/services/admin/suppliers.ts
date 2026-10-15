import { request } from '@umijs/max';
import { AdminSupplierApi } from '@/constants/api';
import type {
  ApiResponse,
  PageData,
  SupplierCreateParams,
  SupplierDetailPublic,
  SupplierListParams,
  SupplierOption,
  SupplierPublic,
  SupplierUpdateParams,
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

/** POST /api/v1/admin/suppliers/options */
export async function fetchSupplierOptions(
  params: { keyword?: string } = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SupplierOption[]>>(
    AdminSupplierApi.OPTIONS,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        page: 1,
        page_size: 100,
      },
      ...options,
    },
  );
  return unwrapApiData<SupplierOption[]>(res) ?? [];
}

/** POST /api/v1/admin/suppliers/list */
export async function fetchSupplierList(
  params: SupplierListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<SupplierPublic>>>(
    AdminSupplierApi.LIST,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<SupplierPublic>>(res),
    '获取供应商列表失败',
  );
}

/** POST /api/v1/admin/suppliers/detail */
export async function fetchSupplierDetail(
  id: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SupplierDetailPublic>>(
    AdminSupplierApi.DETAIL,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<SupplierDetailPublic>(res),
    '获取供应商详情失败',
  );
}

/** POST /api/v1/admin/suppliers/create */
export async function createSupplier(
  params: SupplierCreateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SupplierPublic>>(
    AdminSupplierApi.CREATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<SupplierPublic>(res), '创建供应商失败');
}

/** POST /api/v1/admin/suppliers/update */
export async function updateSupplier(
  params: SupplierUpdateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SupplierPublic>>(
    AdminSupplierApi.UPDATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<SupplierPublic>(res), '更新供应商失败');
}

/** POST /api/v1/admin/suppliers/delete —— 需平台管理员 */
export async function deleteSupplier(id: number, options?: RequestOptions) {
  await request<ApiResponse<Record<string, never>>>(AdminSupplierApi.DELETE, {
    method: 'POST',
    data: { id },
    ...options,
  });
}
