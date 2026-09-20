import { request } from '@umijs/max';
import { CommonUtilsApi } from '@/constants/api';
import type {
  ApiResponse,
  DhgateUploadImgParams,
  DhgateUploadImgPublic,
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

/** POST /api/v1/common/utils/dhgate/uploadimg */
export async function uploadDhgateImage(
  params: DhgateUploadImgParams,
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

  const res = await request<ApiResponse<DhgateUploadImgPublic>>(
    CommonUtilsApi.DHGATE_UPLOAD_IMG,
    {
      method: 'POST',
      data: formData,
      timeout: 120000,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<DhgateUploadImgPublic>(res),
    '图片微调失败',
  );
}
