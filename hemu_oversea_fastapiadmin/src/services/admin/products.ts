import { request } from '@umijs/max';
import { AdminProductApi } from '@/constants/api';
import type {
  ApiResponse,
  DhProductDetailPublic,
  DhProductGroupGetParams,
  DhProductGroupListParams,
  DhProductGroupPublic,
  DhProductListParams,
  DhProductPublic,
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

/** POST /api/v1/admin/product/dh/list */
export async function fetchDhProductList(
  params: DhProductListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<DhProductPublic>>>(
    AdminProductApi.DH_PRODUCT_LIST,
    {
      method: 'POST',
      data: {
        type: params.type ?? 1,
        state: params.state,
        item_code: params.item_code,
        item_name: params.item_name,
        store_id: params.store_id,
        cate_pub_id: params.cate_pub_id,
        sort: params.sort ?? 0,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<DhProductPublic>>(res),
    '获取商品列表失败',
  );
}

/** POST /api/v1/admin/product/dh/detail */
export async function fetchDhProductDetail(
  id: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhProductDetailPublic>>(
    AdminProductApi.DH_PRODUCT_DETAIL,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhProductDetailPublic>(res),
    '获取商品详情失败',
  );
}

/** POST /api/v1/admin/product/dh/group/get */
export async function fetchDhProductGroup(
  params: DhProductGroupGetParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhProductGroupPublic>>(
    AdminProductApi.DH_PRODUCT_GROUP_GET,
    {
      method: 'POST',
      data: {
        store_id: params.store_id,
        group_id: params.group_id,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhProductGroupPublic>(res),
    '获取产品分组失败',
  );
}

/** POST /api/v1/admin/product/dh/group/list */
export async function fetchDhProductGroupList(
  params: DhProductGroupListParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<DhProductGroupPublic>>>(
    AdminProductApi.DH_PRODUCT_GROUP_LIST,
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
