import { request } from '@umijs/max';
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
import { staffApiPrefix } from './rbac';

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

/** 按当前登录门户身份调用 platform-staff 或 supplier-staff */
export async function fetchStaffList(
  portalRole: string | undefined,
  params: SupplierStaffListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<UserPublic>>>(
    `${staffApiPrefix(portalRole)}/list`,
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

export async function createStaff(
  portalRole: string | undefined,
  params: SupplierStaffCreateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<UserPublic>>(
    `${staffApiPrefix(portalRole)}/create`,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<UserPublic>(res), '创建员工失败');
}

export async function updateStaff(
  portalRole: string | undefined,
  params: SupplierStaffUpdateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<UserPublic>>(
    `${staffApiPrefix(portalRole)}/update`,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<UserPublic>(res), '更新员工失败');
}

export async function updateStaffStatus(
  portalRole: string | undefined,
  params: SupplierStaffStatusParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<UserPublic>>(
    `${staffApiPrefix(portalRole)}/status`,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<UserPublic>(res), '更新员工状态失败');
}

export async function deleteStaff(
  portalRole: string | undefined,
  id: number,
  options?: RequestOptions,
) {
  await request<ApiResponse<Record<string, never>>>(
    `${staffApiPrefix(portalRole)}/delete`,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
}

/** @deprecated 使用 createStaff */
export const createSupplierStaff = (
  params: SupplierStaffCreateParams,
  options?: RequestOptions,
) => createStaff('supplier_admin', params, options);

/** @deprecated */
export const fetchSupplierStaffList = (
  params?: SupplierStaffListParams,
  options?: RequestOptions,
) => fetchStaffList('supplier_admin', params, options);

/** @deprecated */
export const updateSupplierStaff = (
  params: SupplierStaffUpdateParams,
  options?: RequestOptions,
) => updateStaff('supplier_admin', params, options);

/** @deprecated */
export const updateSupplierStaffStatus = (
  params: SupplierStaffStatusParams,
  options?: RequestOptions,
) => updateStaffStatus('supplier_admin', params, options);

/** @deprecated */
export const deleteSupplierStaff = (id: number, options?: RequestOptions) =>
  deleteStaff('supplier_admin', id, options);
