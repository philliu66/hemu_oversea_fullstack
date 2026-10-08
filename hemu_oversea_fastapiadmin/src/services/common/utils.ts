import { request } from '@umijs/max';
import { CommonUtilsApi } from '@/constants/api';
import type {
  ApiResponse,
  DhMeasuresUnitPublic,
  DhSkuBasePricePublic,
  DhgateImgInfoPublic,
  DhgateTweakImgParams,
  DhgateTweakImgPublic,
  DhgateUploadImgParams,
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

/** POST /api/v1/common/utils/dhgate/uploadimg — 直接上传图片到敦煌相册 */
export async function uploadDhgateImage(
  params: DhgateUploadImgParams,
  options?: RequestOptions,
) {
  const formData = new FormData();
  formData.append('store_id', String(params.store_id));
  formData.append('img', params.file, params.filename || 'upload.jpg');

  const res = await request<ApiResponse<DhgateImgInfoPublic>>(
    CommonUtilsApi.DHGATE_UPLOAD_IMG,
    {
      method: 'POST',
      data: formData,
      timeout: 120000,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhgateImgInfoPublic>(res),
    '图片上传失败',
  );
}

/** POST /api/v1/common/utils/dhgate/tweakimg — 微调并上传 */
export async function tweakDhgateImage(
  params: DhgateTweakImgParams,
  options?: RequestOptions,
) {
  const formData = new FormData();
  formData.append('store_id', String(params.store_id));
  if (params.img_url) {
    formData.append('img_url', params.img_url);
  }
  if (params.img_md5) {
    formData.append('img_md5', params.img_md5);
  }
  if (params.type) {
    formData.append('type', params.type);
  }
  if (params.file) {
    formData.append(
      'img_base64',
      params.file,
      params.filename || 'upload.jpg',
    );
  }

  const res = await request<ApiResponse<DhgateTweakImgPublic>>(
    CommonUtilsApi.DHGATE_TWEAK_IMG,
    {
      method: 'POST',
      data: formData,
      timeout: 120000,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhgateTweakImgPublic>(res),
    '图片微调失败',
  );
}

/** POST /api/v1/common/utils/dhgate/getmeasuresunitlist */
export async function fetchDhMeasuresUnitList(options?: RequestOptions) {
  const res = await request<ApiResponse<DhMeasuresUnitPublic[]>>(
    CommonUtilsApi.DHGATE_GET_MEASURES_UNIT_LIST,
    {
      method: 'POST',
      data: {},
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhMeasuresUnitPublic[]>(res),
    '获取计件单位列表失败',
  );
}

/** GET /api/v1/common/utils/dhgate/getskubaseprice */
export async function fetchDhSkuBasePrice(
  params: { supplier_id: number; sku_code: string },
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<DhSkuBasePricePublic>>(
    CommonUtilsApi.DHGATE_GET_SKU_BASE_PRICE,
    {
      method: 'GET',
      params: {
        supplier_id: params.supplier_id,
        sku_code: params.sku_code,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhSkuBasePricePublic>(res),
    '获取 SKU 基础价格失败',
  );
}
