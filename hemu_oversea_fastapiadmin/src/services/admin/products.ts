import { request } from '@umijs/max';
import { AdminProductApi } from '@/constants/api';
import type {
  ApiResponse,
  DhProductDetailPublic,
  DhProductListParams,
  DhProductPublic,
  DhProductPublishParams,
  DhProductPublishPublic,
  DhProductSyncParams,
  DhProductSyncPublic,
  DhSkuListPriceParams,
  DhSkuListPricePublic,
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
        supplier_id: params.supplier_id,
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

/** POST /api/v1/admin/product/dh/skulistprice/get */
export async function fetchDhSkuListPrice(
  params: DhSkuListPriceParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhSkuListPricePublic>>(
    AdminProductApi.DH_SKU_LIST_PRICE,
    {
      method: 'POST',
      data: {
        supplier_id: params.supplier_id,
        sku_code: params.sku_code,
        store_id: params.store_id,
        cate_id: params.cate_id,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhSkuListPricePublic>(res),
    '计算 SKU 标价失败',
  );
}

/** POST /api/v1/admin/product/dh/sync */
export async function syncDhProduct(
  params: DhProductSyncParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhProductSyncPublic>>(
    AdminProductApi.DH_PRODUCT_SYNC,
    {
      method: 'POST',
      data: {
        store_id: params.store_id,
        item_code: params.item_code,
        site_id: params.site_id ?? 'EN',
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhProductSyncPublic>(res),
    '同步敦煌商品失败',
  );
}

/** POST /api/v1/admin/product/dh/publish */
export async function publishDhProduct(
  params: DhProductPublishParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhProductPublishPublic>>(
    AdminProductApi.DH_PRODUCT_PUBLISH,
    {
      method: 'POST',
      data: {
        type: params.type ?? 'addfission',
        mission_data_fission_id: params.mission_data_fission_id,
        info: params.info ?? null,
        supplier_id: params.supplier_id,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhProductPublishPublic>(res),
    '发布商品失败',
  );
}
