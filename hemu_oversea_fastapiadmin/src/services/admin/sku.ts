import { request } from '@umijs/max';
import { AdminSkuApi } from '@/constants/api';
import type {
  ApiResponse,
  DhSkuBaseInfoListParams,
  DhSkuBaseInfoPublic,
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

/** POST /api/v1/admin/sku/dh/base-info/list */
export async function fetchSkuBaseInfoList(
  params: DhSkuBaseInfoListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<DhSkuBaseInfoPublic>>>(
    AdminSkuApi.BASE_INFO_LIST,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        page: params.page ?? 1,
        page_size: params.page_size ?? 5000,
        supplier_id: params.supplier_id,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<DhSkuBaseInfoPublic>>(res),
    '获取 SKU 列表失败',
  );
}
