import type { DhProductDetailPublic } from '@/types/api';

export const PRODUCT_LIST_PATH = '/product/list';
export const PRODUCT_CREATE_PATH = '/product/create';

/** 商品页业务模式：同一组件，路径区分 */
export type ProductPageMode = 'create' | 'copy' | 'view' | 'edit';

export type ProductPageRouteState = {
  mode: ProductPageMode;
  /** view / edit 的商品 id */
  productId?: number;
  /** copy 的源商品 id */
  fromId?: number;
};

export function productDetailPath(id: number) {
  return `/product/detail/${id}`;
}

export function productEditPath(id: number) {
  return `/product/edit/${id}`;
}

export function productCreatePath(options?: { from?: number }) {
  if (options?.from) {
    return `${PRODUCT_CREATE_PATH}?from=${options.from}`;
  }
  return PRODUCT_CREATE_PATH;
}

export function parseProductId(value?: string | null) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

/**
 * 从 pathname + search 解析商品页模式。
 * - /product/create
 * - /product/create?from=123
 * - /product/detail/:id
 * - /product/edit/:id
 */
export function resolveProductPageRoute(
  pathname: string,
  search = '',
): ProductPageRouteState {
  const query = new URLSearchParams(
    search.startsWith('?') ? search.slice(1) : search,
  );
  const fromId = parseProductId(query.get('from'));

  if (pathname.startsWith('/product/create')) {
    if (fromId) {
      return { mode: 'copy', fromId };
    }
    return { mode: 'create' };
  }

  const segments = pathname.split('/').filter(Boolean);
  const idParam = segments[segments.length - 1];
  const productId = parseProductId(idParam);

  if (pathname.startsWith('/product/edit/')) {
    return { mode: 'edit', productId };
  }

  return { mode: 'view', productId };
}

export function isProductPageEditable(mode: ProductPageMode) {
  return mode === 'create' || mode === 'copy' || mode === 'edit';
}

/** product_dh.sync_state：1=成功，0=失败 */
export function formatSyncState(
  syncState: string | null | undefined,
  successText: string,
  failText: string,
): string {
  if (syncState === '1') {
    return successText;
  }
  if (syncState === '0') {
    return failText;
  }
  const text = syncState?.trim();
  return text || '-';
}

/** 新建商品的空白草稿（本地态，尚未落库） */
export function createEmptyProductDetail(
  partial?: Partial<DhProductDetailPublic>,
): DhProductDetailPublic {
  return {
    id: 0,
    store_id: 0,
    item_code: '',
    site_id: 'EN',
    is_seed: '0',
    supplier_id: null,
    cate_pub_id: null,
    state: null,
    item_name: null,
    short_desc: null,
    html_content: null,
    key_word1: null,
    key_word2: null,
    key_word3: null,
    video_url: null,
    min_wholesale_qty: null,
    max_sale_qty: null,
    leading_time: null,
    price_config_type: null,
    gross_weight: null,
    length: null,
    width: null,
    height: null,
    packing_quantity: null,
    price_min: null,
    price_max: null,
    sku_count: null,
    total_inventory: null,
    issample: null,
    is_dh_optimized: null,
    vaild_day: null,
    expire_date: null,
    operate_date: null,
    last_synced_at: null,
    sync_state: '',
    item_img_list: [],
    sku_list: [],
    category: null,
    item_group_id: null,
    attr_list: [],
    item_spec_self_def_list: [],
    ...partial,
  };
}

/** 复制：保留可编辑内容，清空平台身份字段 */
export function toCopyProductDetail(
  source: DhProductDetailPublic,
): DhProductDetailPublic {
  return {
    ...source,
    id: 0,
    item_code: '',
    state: null,
    last_synced_at: null,
    expire_date: null,
    operate_date: null,
    sync_state: '',
    sku_list: (source.sku_list || []).map((sku) => ({
      ...sku,
      id: 0,
      sku_id: null,
    })),
  };
}
