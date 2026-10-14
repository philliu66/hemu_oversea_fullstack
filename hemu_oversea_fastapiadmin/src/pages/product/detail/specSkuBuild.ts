import type {
  DhItemSkuAttrValPublic,
  DhProductSelectedAttrPublic,
  DhProductSkuPublic,
  DhProductSpecSelfDefPublic,
} from '@/types/api';

type SpecDimValue = {
  attr_id: string | null;
  attr_val_id: string | null;
  size_spec_type: string;
  label: string;
};

function valueLabel(item: {
  attr_val_id?: string | null;
  line_attrval_name?: string | null;
  line_attrval_name_cn?: string | null;
}): string {
  return (
    item.line_attrval_name_cn?.trim() ||
    item.line_attrval_name?.trim() ||
    String(item.attr_val_id ?? '').trim() ||
    ''
  );
}

/**
 * 构建价格属性维度。
 * 若某个已出现的价格属性没有任何有效值，返回 null（无法生成组合）。
 */
function buildPriceDimensions(
  priceAttrs: DhProductSelectedAttrPublic[],
): SpecDimValue[][] | null {
  const dims: SpecDimValue[][] = [];
  for (const attr of priceAttrs) {
    const values = (attr.values || [])
      .map((item) => {
        const attrValId = String(item.attr_val_id ?? '').trim();
        const label = valueLabel(item);
        if (!attrValId && !label) {
          return null;
        }
        return {
          attr_id: String(attr.attr_id),
          attr_val_id: attrValId || null,
          size_spec_type: '1',
          label: label || attrValId,
        } satisfies SpecDimValue;
      })
      .filter((item): item is SpecDimValue => Boolean(item));
    if (values.length === 0) {
      return null;
    }
    dims.push(values);
  }
  return dims;
}

function buildCustomSpecDimension(
  specs: DhProductSpecSelfDefPublic[],
): SpecDimValue[] | null {
  const values = (specs || [])
    .map((item) => {
      const attrValId = String(item.attr_val_id ?? '').trim();
      const label =
        item.attr_val_name?.trim() ||
        attrValId ||
        '';
      if (!attrValId && !label) {
        return null;
      }
      return {
        attr_id: null,
        attr_val_id: attrValId || null,
        size_spec_type: '3',
        label,
      } satisfies SpecDimValue;
    })
    .filter((item): item is SpecDimValue => Boolean(item));
  if (values.length === 0) {
    return null;
  }
  return values;
}

function cartesian<T>(dims: T[][]): T[][] {
  if (dims.length === 0) {
    return [];
  }
  return dims.reduce<T[][]>((acc, dim) => {
    if (dim.length === 0) {
      return [];
    }
    if (acc.length === 0) {
      return dim.map((item) => [item]);
    }
    const next: T[][] = [];
    for (const prev of acc) {
      for (const item of dim) {
        next.push([...prev, item]);
      }
    }
    return next;
  }, []);
}

/**
 * 规格组合签名：用于判断价格属性 / 自定义规格变更是否影响 SKU 笛卡尔积。
 */
export function buildSpecComboSignature(
  priceAttrs: DhProductSelectedAttrPublic[] | undefined,
  specs: DhProductSpecSelfDefPublic[] | undefined,
): string {
  const pricePart = (priceAttrs || [])
    .map((attr) => {
      const vals = (attr.values || [])
        .map(
          (item) =>
            String(item.attr_val_id ?? '').trim() ||
            valueLabel(item),
        )
        .filter(Boolean)
        .sort()
        .join(',');
      return `${attr.attr_id}:${vals}`;
    })
    .sort()
    .join('|');
  const specPart = (specs || [])
    .map(
      (item) =>
        String(item.attr_val_id ?? '').trim() ||
        (item.attr_val_name || '').trim(),
    )
    .filter(Boolean)
    .sort()
    .join(',');
  return `${pricePart}#${specPart}`;
}

/**
 * 按已选价格属性值 × 自定义规格值生成 SKU 列表（笛卡尔积）。
 * 无任何维度时返回空数组。
 */
export function buildSkuListFromSpecAttrs(
  priceAttrs: DhProductSelectedAttrPublic[] | undefined,
  specs: DhProductSpecSelfDefPublic[] | undefined,
): DhProductSkuPublic[] {
  const priceDims = buildPriceDimensions(priceAttrs || []);
  if (priceDims === null) {
    return [];
  }
  const customDim = buildCustomSpecDimension(specs || []);
  const effectiveDims: SpecDimValue[][] =
    priceDims.length > 0
      ? customDim
        ? [...priceDims, customDim]
        : priceDims
      : customDim
        ? [customDim]
        : [];

  if (effectiveDims.length === 0) {
    return [];
  }

  return cartesian(effectiveDims).map((combo, index) => {
    const item_sku_attr_value_list: DhItemSkuAttrValPublic[] = combo.map(
      (item) => ({
        attr_id: item.attr_id,
        attr_val_id: item.attr_val_id,
        attr_val_code: null,
        size_spec_type: item.size_spec_type,
      }),
    );
    const labels = combo.map((item) => item.label).filter(Boolean);
    const keyParts = combo.map(
      (item) => item.attr_val_id || item.label || '',
    );
    return {
      id: 0,
      sku_id: null,
      sku_code: null,
      sku_md5: `gen-${index}-${keyParts.join('-')}`,
      retail_price: null,
      inventory: null,
      sale_status: null,
      pic_url: null,
      attr_combo_text: labels.join(' / ') || null,
      item_sku_attr_value_list,
      item_sku_inventory_list: [],
      shipto_country_price_list: [],
    };
  });
}
