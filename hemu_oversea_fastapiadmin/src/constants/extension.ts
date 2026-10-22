/** 与 hemu_oversea_browser_extension 协议对齐 */

export const EXT_PROTOCOL_VERSION = 1;
export const EXT_ADMIN_PAGE_SOURCE = 'hemu-admin-page' as const;
export const EXT_SOURCE = 'hemu-browser-ext' as const;

/** 热卖业务类型（扩展 features/hotsell） */
export const EXT_BUSINESS_HOTSELL = 'hotsell' as const;

/** 系统配置中热卖相关的 key */
export const CONFIG_KEY_MISSION_HOTSALE_DH = 'mission_hotsale_dh_config' as const;

/**
 * 扩展 START.mode
 * - list_collect：列表采集（部分信息，对应 collectConfig）
 * - fetch_product_rsc：插件 background 直拉商品 RSC（对应 fillConfig + 商品 openUrl）
 *
 * START 必须嵌套传配置，禁止把 collect/fill 字段扁平 merge，以免 alertTip 等同名字段串扰。
 */
export const EXT_HOTSELL_MODE_LIST_COLLECT = 'list_collect' as const;
export const EXT_HOTSELL_MODE_FETCH_PRODUCT_RSC = 'fetch_product_rsc' as const;

export type HotsaleCollectConfig = {
  openUrl?: string;
  watchApiUrl?: string;
  alertTip?: string;
  [key: string]: unknown;
};

export type HotsaleFillConfig = {
  /** 预留；background 直拉路径暂不展示页内 tip */
  alertTip?: string;
  /** 兼容旧字段名 */
  popTip?: string;
  [key: string]: unknown;
};

export type MissionHotsaleDhConfig = {
  collectConfig?: HotsaleCollectConfig;
  fillConfig?: HotsaleFillConfig;
  [key: string]: unknown;
};

/** 列表采集 START（嵌套 collectConfig） */
export type HotsellStartListCollectPayload = {
  mode: typeof EXT_HOTSELL_MODE_LIST_COLLECT;
  collectConfig: HotsaleCollectConfig;
};

/** 商品 RSC 取数 START（嵌套 fillConfig + 商品 openUrl；同步回传 Flight） */
export type HotsellStartFetchProductRscPayload = {
  mode: typeof EXT_HOTSELL_MODE_FETCH_PRODUCT_RSC;
  openUrl: string;
  fillConfig: HotsaleFillConfig;
};

export type HotsellStartPayload =
  | HotsellStartListCollectPayload
  | HotsellStartFetchProductRscPayload;

/** 扩展 START fetch_product_rsc 的回复 payload */
export type HotsellFetchProductRscResult = {
  ok?: boolean;
  error?: string;
  message?: string;
  mode?: typeof EXT_HOTSELL_MODE_FETCH_PRODUCT_RSC;
  openUrl?: string;
  httpStatus?: number;
  contentType?: string;
  flightContent?: string;
  elapsedMs?: number;
  fillConfig?: HotsaleFillConfig;
};

export function asMissionHotsaleDhConfig(
  value: unknown,
): MissionHotsaleDhConfig | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as MissionHotsaleDhConfig;
}
