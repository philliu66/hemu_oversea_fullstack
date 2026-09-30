import { request } from '@umijs/max';
import { AdminStoreApi } from '@/constants/api';
import type {
  ApiResponse,
  DhProductGroupListParams,
  DhProductGroupPublic,
  PageData,
  StoreAftersaleTemplatePublic,
  StoreAuthorizePublic,
  StoreBaseDiscountPublic,
  StoreCreateParams,
  StoreDetailPublic,
  StoreInspectionPunishParams,
  StoreInspectionPunishPublic,
  StoreListParams,
  StorePublic,
  StoreShippingTemplatePublic,
  StoreUpdateParams,
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

/** POST /api/v1/admin/stores/list */
export async function fetchStoreList(
  params: StoreListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<StorePublic>>>(
    AdminStoreApi.LIST,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        store_type: params.store_type,
        supplier_id: params.supplier_id,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<StorePublic>>(res),
    '获取店铺列表失败',
  );
}

/** POST /api/v1/admin/stores/detail */
export async function fetchStoreDetail(id: number, options?: RequestOptions) {
  const res = await request<ApiResponse<StoreDetailPublic>>(
    AdminStoreApi.DETAIL,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<StoreDetailPublic>(res),
    '获取店铺详情失败',
  );
}

/** POST /api/v1/admin/stores/base-discount/get */
export async function fetchStoreBaseDiscount(
  id: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<StoreBaseDiscountPublic>>(
    AdminStoreApi.BASE_DISCOUNT,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<StoreBaseDiscountPublic>(res),
    '获取店铺基础折扣率失败',
  );
}

/** POST /api/v1/admin/stores/authorize-url */
export async function fetchStoreAuthorizeUrl(
  id: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<StoreAuthorizePublic>>(
    AdminStoreApi.AUTHORIZE_URL,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<StoreAuthorizePublic>(res),
    '获取授权链接失败',
  );
}

/** POST /api/v1/admin/stores/create */
export async function createStore(
  params: StoreCreateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<StorePublic>>(AdminStoreApi.CREATE, {
    method: 'POST',
    data: params,
    ...options,
  });
  return requireData(unwrapApiData<StorePublic>(res), '创建店铺失败');
}

/** POST /api/v1/admin/stores/update */
export async function updateStore(
  params: StoreUpdateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<StorePublic>>(AdminStoreApi.UPDATE, {
    method: 'POST',
    data: params,
    ...options,
  });
  return requireData(unwrapApiData<StorePublic>(res), '更新店铺失败');
}

/** POST /api/v1/admin/stores/delete */
export async function deleteStore(id: number, options?: RequestOptions) {
  await request<ApiResponse<Record<string, never>>>(AdminStoreApi.DELETE, {
    method: 'POST',
    data: { id },
    ...options,
  });
}

/** POST /api/v1/admin/stores/inspection/punish */
export async function fetchStoreInspectionPunish(
  params: StoreInspectionPunishParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<StoreInspectionPunishPublic>>(
    AdminStoreApi.INSPECTION_PUNISH,
    {
      method: 'POST',
      data: {
        supplier_id: params.supplier_id,
        store_id: params.store_id,
        query_days: params.query_days,
        page_no: params.page_no ?? 1,
        page_size: params.page_size ?? 100,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<StoreInspectionPunishPublic>(res),
    '获取店铺巡检处罚信息失败',
  );
}

/** POST /api/v1/admin/stores/groups */
export async function fetchStoreProductGroups(
  params: DhProductGroupListParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<DhProductGroupPublic>>>(
    AdminStoreApi.GROUPS,
    {
      method: 'POST',
      data: {
        store_id: params.store_id,
        keyword: params.keyword,
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<DhProductGroupPublic>>(res),
    '获取产品分组列表失败',
  );
}

/** POST /api/v1/admin/stores/shipping-template/list */
export async function fetchStoreShippingTemplates(
  storeId: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<StoreShippingTemplatePublic[]>>(
    AdminStoreApi.SHIPPING_TEMPLATE_LIST,
    {
      method: 'POST',
      data: { store_id: storeId },
      ...options,
    },
  );
  return unwrapApiData<StoreShippingTemplatePublic[]>(res) ?? [];
}

/** POST /api/v1/admin/stores/aftersale-template/list */
export async function fetchStoreAftersaleTemplates(
  storeId: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<StoreAftersaleTemplatePublic[]>>(
    AdminStoreApi.AFTERSALE_TEMPLATE_LIST,
    {
      method: 'POST',
      data: { store_id: storeId },
      ...options,
    },
  );
  return unwrapApiData<StoreAftersaleTemplatePublic[]>(res) ?? [];
}

