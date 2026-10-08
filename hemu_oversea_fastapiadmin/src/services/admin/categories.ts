import { request } from '@umijs/max';
import { AdminCategoryApi } from '@/constants/api';
import type {
  ApiResponse,
  DhCategoryAttrsPublic,
  DhCategoryListParams,
  DhCategoryPathPublic,
  DhCategoryPublic,
  DhCommissionRatePublic,
  DhSeedCategoryPublic,
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

/** POST /api/v1/admin/categories/dh/list */
export async function fetchDhCategories(
  params: DhCategoryListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhCategoryPublic[]>>(
    AdminCategoryApi.DH_LIST,
    {
      method: 'POST',
      data: {
        parent_id: params.parent_id ?? null,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhCategoryPublic[]>(res),
    '获取商品分类失败',
  );
}

/** POST /api/v1/admin/categories/dh/seed-list */
export async function fetchDhSeedCategories(
  params: DhCategoryListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhSeedCategoryPublic[]>>(
    AdminCategoryApi.DH_SEED_LIST,
    {
      method: 'POST',
      data: {
        parent_id: params.parent_id ?? null,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhSeedCategoryPublic[]>(res),
    '获取种子商品分类失败',
  );
}

/** POST /api/v1/admin/categories/dh/path */
export async function fetchDhCategoryPath(
  id: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhCategoryPathPublic>>(
    AdminCategoryApi.DH_PATH,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhCategoryPathPublic>(res),
    '获取分类全路径失败',
  );
}

/** POST /api/v1/admin/categories/dh/attrs */
export async function fetchDhCategoryAttrs(
  id: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhCategoryAttrsPublic>>(
    AdminCategoryApi.DH_ATTRS,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhCategoryAttrsPublic>(res),
    '获取分类属性失败',
  );
}

/** POST /api/v1/admin/categories/dh/search */
export async function fetchDhCategorySearch(
  params: {
    keyword: string;
    leaf_only?: boolean;
    limit?: number;
  },
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhCategoryPublic[]>>(
    AdminCategoryApi.DH_SEARCH,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        leaf_only: params.leaf_only ?? true,
        limit: params.limit ?? 50,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhCategoryPublic[]>(res),
    '搜索商品分类失败',
  );
}

/** POST /api/v1/admin/categories/dh/commission-rate/get
 * 查询类目佣金率；当前业务暂固定传参考定价类目 ID（000000）。
 */
export async function fetchDhCommissionRate(
  cateId: string,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhCommissionRatePublic>>(
    AdminCategoryApi.DH_COMMISSION_RATE,
    {
      method: 'POST',
      data: { cate_id: cateId },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhCommissionRatePublic>(res),
    '获取类目佣金率失败',
  );
}
