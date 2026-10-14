import { request } from '@umijs/max';
import { AdminTemplateApi } from '@/constants/api';
import type {
  ApiResponse,
  PageData,
  SkuAttrTemplateCreateParams,
  SkuAttrTemplateListItemPublic,
  SkuAttrTemplateListParams,
  SkuAttrTemplateLookupParams,
  SkuAttrTemplateLookupPublic,
  SkuAttrTemplatePublic,
  SkuAttrTemplateUpdateParams,
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

/** POST /api/v1/admin/templates/dh/sku-attr-templates/list */
export async function fetchSkuAttrTemplateList(
  params: SkuAttrTemplateListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<SkuAttrTemplateListItemPublic>>>(
    AdminTemplateApi.SKU_ATTR_LIST,
    {
      method: 'POST',
      data: {
        sku_code: params.sku_code,
        cate_pub_id: params.cate_pub_id,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<SkuAttrTemplateListItemPublic>>(res),
    '获取属性模板列表失败',
  );
}

/** POST /api/v1/admin/templates/dh/sku-attr-templates/detail */
export async function fetchSkuAttrTemplateDetail(
  id: number,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SkuAttrTemplatePublic>>(
    AdminTemplateApi.SKU_ATTR_DETAIL,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<SkuAttrTemplatePublic>(res),
    '获取属性模板详情失败',
  );
}

/** POST /api/v1/admin/templates/dh/sku-attr-templates/create */
export async function createSkuAttrTemplate(
  params: SkuAttrTemplateCreateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SkuAttrTemplatePublic>>(
    AdminTemplateApi.SKU_ATTR_CREATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<SkuAttrTemplatePublic>(res),
    '创建属性模板失败',
  );
}

/** POST /api/v1/admin/templates/dh/sku-attr-templates/update */
export async function updateSkuAttrTemplate(
  params: SkuAttrTemplateUpdateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SkuAttrTemplatePublic>>(
    AdminTemplateApi.SKU_ATTR_UPDATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<SkuAttrTemplatePublic>(res),
    '更新属性模板失败',
  );
}

/** POST /api/v1/admin/templates/dh/sku-attr-templates/delete */
export async function deleteSkuAttrTemplate(
  id: number,
  options?: RequestOptions,
) {
  await request<ApiResponse<Record<string, never>>>(
    AdminTemplateApi.SKU_ATTR_DELETE,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
}

/** POST /api/v1/admin/templates/dh/sku-attr-templates/lookup */
export async function lookupSkuAttrTemplates(
  params: SkuAttrTemplateLookupParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<SkuAttrTemplateLookupPublic>>(
    AdminTemplateApi.SKU_ATTR_LOOKUP,
    {
      method: 'POST',
      data: {
        cate_pub_id: params.cate_pub_id,
        sku_codes: params.sku_codes,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<SkuAttrTemplateLookupPublic>(res),
    '查询属性模板失败',
  );
}
