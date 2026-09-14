import { request } from '@umijs/max';
import { AdminCategoryApi } from '@/constants/api';
import type {
  ApiResponse,
  DhCategoryAttrsPublic,
  DhCategoryListParams,
  DhCategoryPathPublic,
  DhCategoryPublic,
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
