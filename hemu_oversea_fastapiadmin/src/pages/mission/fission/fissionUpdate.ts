import type {
  DhItemSkuAttrValPublic,
  DhItemSkuInventoryPublic,
  DhItemShiptoSkuPricePublic,
  DhProductDetailPublic,
  DhProductImgPublic,
  DhProductSkuPublic,
  DhProductSpecSelfDefPublic,
} from '@/types/api';
import { diffAttrList } from './attrDiff';

export const FISSION_TRACKED_KEYS = [
  'item_name',
  'key_word1',
  'key_word2',
  'key_word3',
  'cate_pub_id',
  'item_group_id',
  'store_id',
  'attr_list',
  'sku_list',
  'item_img_list',
  'item_spec_self_def_list',
  'html_content',
  'short_desc',
  'after_sale_template_id',
  'shipping_model_id',
] as const satisfies readonly (keyof DhProductDetailPublic)[];

function asList<T>(value: T[] | null | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

function textOrNull(value: string | null | undefined): string | null {
  const text = (value ?? '').trim();
  return text || null;
}

/** 价格统一成可比较字符串，避免 1 vs "1" 误判 */
function priceKey(value: string | number | null | undefined): string | null {
  if (value == null || value === '') {
    return null;
  }
  const num = typeof value === 'number' ? value : Number(value);
  if (Number.isFinite(num)) {
    return String(num);
  }
  return String(value).trim() || null;
}

function sortKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortKeysDeep);
  }
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(obj).sort()) {
      sorted[key] = sortKeysDeep(obj[key]);
    }
    return sorted;
  }
  return value;
}

function stableStringify(value: unknown): string {
  return JSON.stringify(sortKeysDeep(value));
}

function normalizeSkuAttr(item: DhItemSkuAttrValPublic) {
  return {
    attr_id: textOrNull(item.attr_id),
    attr_val_id: textOrNull(item.attr_val_id),
    attr_val_code: textOrNull(item.attr_val_code),
    size_spec_type: textOrNull(item.size_spec_type),
  };
}

function normalizeSkuInventory(item: DhItemSkuInventoryPublic) {
  return {
    sku_md5: textOrNull(item.sku_md5),
    inventory_location: textOrNull(item.inventory_location),
    sku_inventory_qty:
      item.sku_inventory_qty == null ? null : Number(item.sku_inventory_qty),
  };
}

function normalizeShiptoPrice(item: DhItemShiptoSkuPricePublic) {
  return {
    region_code: textOrNull(item.region_code),
    retail_price: priceKey(item.retail_price),
  };
}

/** SKU 字段级规范化，忽略 key 顺序与空缺省差异 */
export function normalizeSkuList(
  list: DhProductSkuPublic[] | null | undefined,
): unknown[] {
  return asList(list).map((sku) => ({
    id: sku.id ?? 0,
    sku_id: textOrNull(sku.sku_id),
    sku_code: textOrNull(sku.sku_code),
    sku_md5: textOrNull(sku.sku_md5),
    retail_price: priceKey(sku.retail_price),
    inventory: sku.inventory == null ? null : Number(sku.inventory),
    sale_status: textOrNull(sku.sale_status),
    pic_url: textOrNull(sku.pic_url),
    attr_combo_text: textOrNull(sku.attr_combo_text),
    item_sku_attr_value_list: asList(sku.item_sku_attr_value_list).map(
      normalizeSkuAttr,
    ),
    item_sku_inventory_list: asList(sku.item_sku_inventory_list).map(
      normalizeSkuInventory,
    ),
    shipto_country_price_list: asList(sku.shipto_country_price_list).map(
      normalizeShiptoPrice,
    ),
  }));
}

export function normalizeSpecSelfDefList(
  list: DhProductSpecSelfDefPublic[] | null | undefined,
): unknown[] {
  return asList(list).map((item) => ({
    attr_val_id: textOrNull(item.attr_val_id),
    spec_attr_name: textOrNull(item.spec_attr_name),
    attr_val_name: textOrNull(item.attr_val_name),
    pic_url: textOrNull(item.pic_url),
  }));
}

export function normalizeImgList(
  list: DhProductImgPublic[] | null | undefined,
): unknown[] {
  return asList(list).map((item) => ({
    img_url: textOrNull(item.img_url),
    img_md5: textOrNull(item.img_md5),
    type: textOrNull(item.type),
  }));
}

function valuesEqual(before: unknown, after: unknown): boolean {
  return stableStringify(before) === stableStringify(after);
}

function normalizeTrackedValue(
  key: (typeof FISSION_TRACKED_KEYS)[number],
  value: unknown,
): unknown {
  if (key === 'sku_list') {
    return normalizeSkuList(value as DhProductSkuPublic[] | null | undefined);
  }
  if (key === 'item_spec_self_def_list') {
    return normalizeSpecSelfDefList(
      value as DhProductSpecSelfDefPublic[] | null | undefined,
    );
  }
  if (key === 'item_img_list') {
    return normalizeImgList(value as DhProductImgPublic[] | null | undefined);
  }
  if (value == null) {
    return null;
  }
  if (typeof value === 'string') {
    return textOrNull(value);
  }
  return value;
}

/** 相对最初种子详情计算 update_json（查看变更 / 保存任务数据共用） */
export function buildFissionUpdateData(
  baseline: DhProductDetailPublic,
  current: DhProductDetailPublic,
): Record<string, unknown> {
  const update: Record<string, unknown> = {};
  for (const key of FISSION_TRACKED_KEYS) {
    if (key === 'attr_list') {
      const attrDiff = diffAttrList(baseline.attr_list, current.attr_list);
      if (attrDiff) {
        update.attr_list = attrDiff;
      }
      continue;
    }
    const before = normalizeTrackedValue(key, baseline[key]);
    const after = normalizeTrackedValue(key, current[key]);
    if (!valuesEqual(before, after)) {
      if (key === 'sku_list') {
        update.sku_list = asList(current.sku_list);
      } else if (key === 'item_spec_self_def_list') {
        update.item_spec_self_def_list = asList(current.item_spec_self_def_list);
      } else if (key === 'item_img_list') {
        update.item_img_list = asList(current.item_img_list);
      } else {
        update[key] = current[key] ?? null;
      }
    }
  }
  return update;
}
