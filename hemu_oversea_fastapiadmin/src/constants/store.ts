/** 店铺类型枚举值 */
export const STORE_TYPES = ['dhgate', 'tiktok'] as const;

export type StoreTypeValue = (typeof STORE_TYPES)[number];

export const STORE_TYPE_LABEL: Record<StoreTypeValue, string> = {
  dhgate: 'DHgate',
  tiktok: 'TikTok',
};

/** 授权状态：0 未授权，1 已授权，2 授权已过期 */
export const STORE_OAUTH_STATUS = {
  UNAUTHORIZED: 0,
  AUTHORIZED: 1,
  EXPIRED: 2,
} as const;

export type StoreOauthStatusValue =
  (typeof STORE_OAUTH_STATUS)[keyof typeof STORE_OAUTH_STATUS];

export const STORE_OAUTH_STATUS_LABEL: Record<StoreOauthStatusValue, string> = {
  [STORE_OAUTH_STATUS.UNAUTHORIZED]: '未授权',
  [STORE_OAUTH_STATUS.AUTHORIZED]: '已授权',
  [STORE_OAUTH_STATUS.EXPIRED]: '授权已过期',
};

/** Tag color：未授权 default，已授权 success，已过期 error */
export const STORE_OAUTH_STATUS_COLOR: Record<StoreOauthStatusValue, string> = {
  [STORE_OAUTH_STATUS.UNAUTHORIZED]: 'default',
  [STORE_OAUTH_STATUS.AUTHORIZED]: 'success',
  [STORE_OAUTH_STATUS.EXPIRED]: 'error',
};

/** 授权回调页与店铺列表通信的 postMessage type */
export const STORE_OAUTH_RESULT_MESSAGE_TYPE = 'HEMU_STORE_OAUTH_RESULT';

/** callback → 店铺列表 postMessage 载荷 */
export type StoreOauthResultMessage = {
  type: typeof STORE_OAUTH_RESULT_MESSAGE_TYPE;
  /** success | fail */
  status: 'success' | 'fail';
  /** 提示文案 */
  msg: string;
  /** 成功时后端会带上店铺 ID */
  store_id?: number;
};
