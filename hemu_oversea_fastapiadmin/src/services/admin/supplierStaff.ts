import { request } from '@umijs/max';
import { AdminSupplierStaffApi } from '@/constants/api';
import type {
  ApiResponse,
  PageData,
  SupplierStaffCreateParams,
  SupplierStaffListParams,
  SupplierStaffStatusParams,
  SupplierStaffUpdateParams,
  UserPublic,
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

/** POST /api/v1/admin/supplier-staff/list */
export async function fetchSupplierStaffList(
  params: SupplierStaffListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<UserPublic>>>(
    AdminSupplierStaffApi.LIST,
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
    unwrapApiData<PageData<UserPublic>>(res),
    '获取员工列表失败',
  );
}

/** POST /api/v1/admin/supplier-staff/create */
export async function createSupplierStaff(
  params: SupplierStaffCreateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<UserPublic>>(
    AdminSupplierStaffApi.CREATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<UserPublic>(res), '创建员工失败');
}

/** POST /api/v1/admin/supplier-staff/update */
export async function updateSupplierStaff(
  params: SupplierStaffUpdateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<UserPublic>>(
    AdminSupplierStaffApi.UPDATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<UserPublic>(res), '更新员工失败');
}

/** POST /api/v1/admin/supplier-staff/status */
export async function updateSupplierStaffStatus(
  params: SupplierStaffStatusParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<UserPublic>>(
    AdminSupplierStaffApi.STATUS,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<UserPublic>(res), '更新员工状态失败');
}

/** POST /api/v1/admin/supplier-staff/delete */
export async function deleteSupplierStaff(
  id: number,
  options?: RequestOptions,
) {
  await request<ApiResponse<Record<string, never>>>(
    AdminSupplierStaffApi.DELETE,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
}
