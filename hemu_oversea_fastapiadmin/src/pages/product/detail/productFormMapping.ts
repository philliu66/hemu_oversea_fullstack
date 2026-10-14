import type {
  DhCategoryAttrPublic,
  DhCategoryPublic,
  DhItemInventoryPublic,
  DhItemWeightRangePublic,
  DhItemWholesaleRangePublic,
  DhProductDetailPublic,
  DhProductImgPublic,
  DhProductSelectedAttrPublic,
  DhProductSkuPublic,
  DhProductSpecSelfDefPublic,
} from '@/types/api';

export const DH_CUSTOM_PRODUCT_ATTR_ID = '11';

export type CustomAttrDraft = {
  key: string;
  attr_val_id: string | null;
  attr_name: string;
  content: string;
};

/** 编辑器表单值：可编辑字段全部走 Form，不再镜像到 detail state */
export type ProductFormValues = {
  store_id?: number;
  category_path?: string[];
  cate_pub_id?: string | null;
  item_name?: string;
  key_word1?: string;
  key_word2?: string;
  key_word3?: string;
  item_group_path?: string[];
  customAttrs?: CustomAttrDraft[];
  issample?: string | null;
  vaild_day?: string | null;
  measure_id?: string | null;
  packing_quantity?: number | null;
  min_wholesale_qty?: number | null;
  item_inventory?: DhItemInventoryPublic | null;
  max_sale_qty?: number | null;
  leading_time?: number | null;
  item_img_list?: DhProductImgPublic[];
  /** 类目/规格属性（不含自定义属性 attr_id=11） */
  attr_list?: DhProductSelectedAttrPublic[];
  item_spec_self_def_list?: DhProductSpecSelfDefPublic[];
  sku_list?: DhProductSkuPublic[];
  price_config_type?: string | null;
  item_wholesale_range_list?: DhItemWholesaleRangePublic[];
  gross_weight?: string | number | null;
  length?: string | number | null;
  width?: string | number | null;
  height?: string | number | null;
  item_weight_range?: DhItemWeightRangePublic | null;
  after_sale_template_id?: string | null;
  shipping_model_id?: string | null;
};

function isCustomProductAttr(attr: DhProductSelectedAttrPublic) {
  return String(attr.attr_id) === DH_CUSTOM_PRODUCT_ATTR_ID;
}

export function isPriceProductAttr(attr: DhProductSelectedAttrPublic) {
  return String(attr.is_price_attr) === '1';
}

/** 类目定义：销售/规格属性（对应商品规格区块） */
export function isSaleCategoryAttr(attr: DhCategoryAttrPublic) {
  return String(attr.sale_attr) === '1';
}

export function saleCategoryAttrs(attrs?: DhCategoryAttrPublic[]) {
  return (attrs || []).filter(isSaleCategoryAttr);
}

export function nonSaleCategoryAttrs(attrs?: DhCategoryAttrPublic[]) {
  return (attrs || []).filter((attr) => !isSaleCategoryAttr(attr));
}

export function categoryProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return (list || []).filter((item) => !isCustomProductAttr(item));
}

export function priceProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return categoryProductAttrs(list).filter(isPriceProductAttr);
}

export function nonPriceProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return categoryProductAttrs(list).filter((item) => !isPriceProductAttr(item));
}

/** 从已选 attr_list 中取出属于给定类目属性 ID 的项（不含自定义 attr_id=11） */
export function selectedAttrsForCategoryIds(
  list: DhProductSelectedAttrPublic[] | undefined,
  categoryAttrIds: Iterable<string>,
): DhProductSelectedAttrPublic[] {
  const idSet = new Set(
    [...categoryAttrIds].map((id) => String(id).trim()).filter(Boolean),
  );
  return categoryProductAttrs(list).filter((item) =>
    idSet.has(String(item.attr_id)),
  );
}

/**
 * 按类目定义的 sale_attr 同步 attr_list.is_price_attr。
 * 自定义属性不动；销售属性标 1，其余普通类目属性标 0。
 */
export function syncIsPriceAttrByCategory(
  list: DhProductSelectedAttrPublic[] | undefined,
  categoryAttrs: DhCategoryAttrPublic[],
): DhProductSelectedAttrPublic[] {
  const saleIds = new Set(
    saleCategoryAttrs(categoryAttrs).map((item) => String(item.attr_id)),
  );
  return (list || []).map((item) => {
    if (isCustomProductAttr(item)) {
      return item;
    }
    const nextFlag = saleIds.has(String(item.attr_id)) ? '1' : '0';
    if (String(item.is_price_attr ?? '') === nextFlag) {
      return item;
    }
    return { ...item, is_price_attr: nextFlag };
  });
}

export function mergeManagedAttrsIntoList(
  list: DhProductSelectedAttrPublic[] | undefined,
  managedAttrIds: Iterable<string>,
  nextManaged: DhProductSelectedAttrPublic[],
): DhProductSelectedAttrPublic[] {
  const managedIdSet = new Set(
    [...managedAttrIds].map((id) => String(id).trim()).filter(Boolean),
  );
  const others = (list || []).filter(
    (item) => !managedIdSet.has(String(item.attr_id)),
  );
  return [...others, ...nextManaged];
}

/**
 * 切换类目后收敛 attr_list：只保留自定义属性，以及仍属于新类目的类目/规格属性。
 * 新类目无属性时 allowed 为空，原类目属性会被全部清掉。
 */
export function retainAttrsForCategory(
  list: DhProductSelectedAttrPublic[] | undefined,
  categoryAttrIds: Iterable<string>,
): DhProductSelectedAttrPublic[] {
  const allowed = new Set(
    [...categoryAttrIds].map((id) => String(id).trim()).filter(Boolean),
  );
  return (list || []).filter(
    (item) =>
      isCustomProductAttr(item) || allowed.has(String(item.attr_id)),
  );
}

export function patchAttrValuePic(
  list: DhProductSelectedAttrPublic[] | undefined,
  attrId: string,
  attrValId: string,
  picUrl: string | null,
): DhProductSelectedAttrPublic[] {
  const source = list || [];
  let foundAttr = false;
  const next = source.map((attr) => {
    if (String(attr.attr_id) !== String(attrId)) {
      return attr;
    }
    foundAttr = true;
    let foundVal = false;
    const values = (attr.values || []).map((item) => {
      if (String(item.attr_val_id) !== String(attrValId)) {
        return item;
      }
      foundVal = true;
      return { ...item, pic_url: picUrl };
    });
    if (!foundVal) {
      values.push({
        attr_val_id: attrValId,
        attr_name: attr.attr_name,
        attr_name_cn: attr.attr_name_cn,
        line_attrval_name: null,
        line_attrval_name_cn: null,
        pic_url: picUrl,
      });
    }
    return { ...attr, values };
  });
  if (!foundAttr) {
    next.push({
      attr_id: attrId,
      attr_name: null,
      attr_name_cn: null,
      is_price_attr: '1',
      values: [
        {
          attr_val_id: attrValId,
          attr_name: null,
          attr_name_cn: null,
          line_attrval_name: null,
          line_attrval_name_cn: null,
          pic_url: picUrl,
        },
      ],
    });
  }
  return next;
}

export function toCustomAttrDrafts(
  list?: DhProductSelectedAttrPublic[],
): CustomAttrDraft[] {
  return (list || [])
    .filter(isCustomProductAttr)
    .flatMap((item) => item.values || [])
    .map((item, index) => ({
      key: item.attr_val_id || `custom-${index}`,
      attr_val_id: item.attr_val_id ?? null,
      attr_name: (item.attr_name_cn || item.attr_name || '').trim(),
      content: (
        item.line_attrval_name_cn ||
        item.line_attrval_name ||
        ''
      ).trim(),
    }));
}

export function applyCustomAttrDraftsToAttrList(
  list: DhProductSelectedAttrPublic[] | undefined,
  drafts: CustomAttrDraft[],
): DhProductSelectedAttrPublic[] {
  const others = (list || []).filter((item) => !isCustomProductAttr(item));
  const values = drafts
    .map((item, index) => ({
      attr_id: DH_CUSTOM_PRODUCT_ATTR_ID,
      attr_val_id: item.attr_val_id || String(index + 1),
      attr_name: (item.attr_name || '').trim() || null,
      attr_name_cn: null,
      line_attrval_name: (item.content || '').trim() || null,
      line_attrval_name_cn: null,
      pic_url: null,
    }))
    .filter((item) => item.attr_name || item.line_attrval_name);
  if (!values.length) {
    return others;
  }
  return [
    ...others,
    {
      attr_id: DH_CUSTOM_PRODUCT_ATTR_ID,
      attr_name: null,
      attr_name_cn: null,
      values,
    },
  ];
}

export function normalizeCustomAttrDrafts(
  drafts: CustomAttrDraft[] | undefined,
): CustomAttrDraft[] {
  return (drafts || []).map((item, index) => ({
    key: item?.key || `custom-${index}-${Date.now()}`,
    attr_val_id: item?.attr_val_id ?? null,
    attr_name: item?.attr_name ?? '',
    content: item?.content ?? '',
  }));
}

function textOrNull(value: string | null | undefined): string | null {
  const text = value?.trim() ?? '';
  return text || null;
}

/** null / undefined / 非数组 → []，与 Form 往返、diff 对齐 */
export function listOrEmpty<T>(value: T[] | null | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

/** 加载详情 → 表单初始值（不含 item_group_path，分组树就绪后再写） */
export function toProductFormValues(
  data: DhProductDetailPublic,
): ProductFormValues {
  return {
    store_id: data.store_id || undefined,
    category_path: data.cate_pub_id ? [data.cate_pub_id] : undefined,
    cate_pub_id: data.cate_pub_id,
    item_name: data.item_name || '',
    key_word1: data.key_word1 || '',
    key_word2: data.key_word2 || '',
    key_word3: data.key_word3 || '',
    customAttrs: toCustomAttrDrafts(data.attr_list),
    issample: String(data.issample) === '2' ? '2' : '3',
    vaild_day: data.vaild_day,
    measure_id: data.measure_id,
    packing_quantity: data.packing_quantity,
    min_wholesale_qty: data.min_wholesale_qty,
    item_inventory: data.item_inventory ?? null,
    max_sale_qty: data.max_sale_qty,
    leading_time: data.leading_time,
    item_img_list: listOrEmpty(data.item_img_list),
    attr_list: categoryProductAttrs(data.attr_list),
    item_spec_self_def_list: listOrEmpty(data.item_spec_self_def_list),
    sku_list: listOrEmpty(data.sku_list),
    price_config_type: data.price_config_type,
    item_wholesale_range_list: listOrEmpty(data.item_wholesale_range_list),
    gross_weight: data.gross_weight,
    length: data.length,
    width: data.width,
    height: data.height,
    item_weight_range: data.item_weight_range ?? null,
    after_sale_template_id: data.after_sale_template_id ?? null,
    shipping_model_id: data.shipping_model_id ?? null,
  };
}

/** 表单当前值 + 加载基线 → 完整详情快照（提交 / diff 用） */
export function buildDetailFromForm(
  baseline: DhProductDetailPublic,
  values: ProductFormValues,
  category: DhCategoryPublic | null | undefined,
): DhProductDetailPublic {
  const path = values.item_group_path;
  const nextGroupId = Array.isArray(path)
    ? path.filter(Boolean).at(-1)
    : undefined;
  const resolvedCategory =
    category !== undefined ? category : baseline.category;
  const catePubId =
    values.cate_pub_id !== undefined
      ? values.cate_pub_id
      : resolvedCategory?.cate_pub_id ?? baseline.cate_pub_id;

  return {
    ...baseline,
    store_id: values.store_id || baseline.store_id,
    cate_pub_id: catePubId ?? null,
    category: resolvedCategory ?? null,
    item_name:
      values.item_name === undefined
        ? baseline.item_name
        : textOrNull(values.item_name),
    key_word1:
      values.key_word1 === undefined
        ? baseline.key_word1
        : textOrNull(values.key_word1),
    key_word2:
      values.key_word2 === undefined
        ? baseline.key_word2
        : textOrNull(values.key_word2),
    key_word3:
      values.key_word3 === undefined
        ? baseline.key_word3
        : textOrNull(values.key_word3),
    item_group_id:
      nextGroupId !== undefined ? String(nextGroupId) : baseline.item_group_id,
    issample:
      values.issample !== undefined ? values.issample : baseline.issample,
    vaild_day:
      values.vaild_day !== undefined ? values.vaild_day : baseline.vaild_day,
    measure_id:
      values.measure_id !== undefined ? values.measure_id : baseline.measure_id,
    packing_quantity:
      values.packing_quantity !== undefined
        ? values.packing_quantity
        : baseline.packing_quantity,
    min_wholesale_qty:
      values.min_wholesale_qty !== undefined
        ? values.min_wholesale_qty
        : baseline.min_wholesale_qty,
    item_inventory:
      values.item_inventory !== undefined
        ? values.item_inventory
        : baseline.item_inventory,
    max_sale_qty:
      values.max_sale_qty !== undefined
        ? values.max_sale_qty
        : baseline.max_sale_qty,
    leading_time:
      values.leading_time !== undefined
        ? values.leading_time
        : baseline.leading_time,
    item_img_list: listOrEmpty(
      values.item_img_list ?? baseline.item_img_list,
    ),
    attr_list: applyCustomAttrDraftsToAttrList(
      values.attr_list,
      normalizeCustomAttrDrafts(values.customAttrs),
    ),
    item_spec_self_def_list: listOrEmpty(
      values.item_spec_self_def_list ?? baseline.item_spec_self_def_list,
    ),
    sku_list: listOrEmpty(values.sku_list ?? baseline.sku_list),
    price_config_type:
      values.price_config_type !== undefined
        ? values.price_config_type
        : baseline.price_config_type,
    item_wholesale_range_list: listOrEmpty(
      values.item_wholesale_range_list ?? baseline.item_wholesale_range_list,
    ),
    gross_weight:
      values.gross_weight !== undefined
        ? values.gross_weight
        : baseline.gross_weight,
    length: values.length !== undefined ? values.length : baseline.length,
    width: values.width !== undefined ? values.width : baseline.width,
    height: values.height !== undefined ? values.height : baseline.height,
    item_weight_range:
      values.item_weight_range !== undefined
        ? values.item_weight_range
        : baseline.item_weight_range,
    after_sale_template_id:
      values.after_sale_template_id !== undefined
        ? values.after_sale_template_id
        : baseline.after_sale_template_id,
    shipping_model_id:
      values.shipping_model_id !== undefined
        ? values.shipping_model_id
        : baseline.shipping_model_id,
  };
}
