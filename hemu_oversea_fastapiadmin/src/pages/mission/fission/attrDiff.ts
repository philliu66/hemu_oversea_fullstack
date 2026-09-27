import type {
  DhProductSelectedAttrPublic,
  DhProductSelectedAttrValPublic,
} from '@/types/api';

const CUSTOM_ATTR_ID = '11';

function text(value: string | null | undefined): string {
  return (value ?? '').trim();
}

function valueSignature(value: DhProductSelectedAttrValPublic): string {
  return [
    text(value.attr_val_id),
    text(value.attr_name_cn) || text(value.attr_name),
    text(value.line_attrval_name_cn) || text(value.line_attrval_name),
    text(value.pic_url),
    text(value.brand_id),
  ].join('\u0001');
}

function valueKey(
  attrId: string,
  value: DhProductSelectedAttrValPublic,
  index: number,
): string {
  const id = text(value.attr_val_id);
  if (attrId === CUSTOM_ATTR_ID) {
    return id || `name:${text(value.attr_name_cn) || text(value.attr_name)}`;
  }
  return id || String(index);
}

function diffValues(
  attrId: string,
  before: DhProductSelectedAttrValPublic[] | undefined,
  after: DhProductSelectedAttrValPublic[] | undefined,
): DhProductSelectedAttrValPublic[] {
  const beforeList = before || [];
  const afterList = after || [];
  const beforeMap = new Map(
    beforeList.map((item, index) => [valueKey(attrId, item, index), item]),
  );
  const afterMap = new Map(
    afterList.map((item, index) => [valueKey(attrId, item, index), item]),
  );
  const changed: DhProductSelectedAttrValPublic[] = [];
  for (const key of new Set([...beforeMap.keys(), ...afterMap.keys()])) {
    const prev = beforeMap.get(key);
    const next = afterMap.get(key);
    if (!next) {
      if (prev) {
        changed.push(prev);
      }
      continue;
    }
    if (!prev || valueSignature(prev) !== valueSignature(next)) {
      changed.push(next);
    }
  }
  return changed;
}

/** 按属性 ID 对比。只保留有变化的属性值；属性 ID 增减时保留该属性的全部值。 */
export function diffAttrList(
  before: DhProductSelectedAttrPublic[] | undefined,
  after: DhProductSelectedAttrPublic[] | undefined,
): DhProductSelectedAttrPublic[] | null {
  const beforeMap = new Map(
    (before || []).map((item) => [String(item.attr_id), item]),
  );
  const afterMap = new Map(
    (after || []).map((item) => [String(item.attr_id), item]),
  );
  const changed: DhProductSelectedAttrPublic[] = [];
  for (const attrId of new Set([...beforeMap.keys(), ...afterMap.keys()])) {
    const prev = beforeMap.get(attrId);
    const next = afterMap.get(attrId);
    if (!prev || !next) {
      const source = next ?? prev;
      if (source) {
        changed.push(source);
      }
      continue;
    }
    const values = diffValues(attrId, prev.values, next.values);
    if (!values.length) {
      continue;
    }
    changed.push({
      attr_id: next.attr_id,
      attr_name: next.attr_name,
      attr_name_cn: next.attr_name_cn,
      is_brand: next.is_brand,
      is_price_attr: next.is_price_attr,
      values,
    });
  }
  return changed.length ? changed : null;
}

export function customAttrValueChanged(
  values: DhProductSelectedAttrValPublic[] | undefined,
  row: { attr_val_id?: string | null; attr_name?: string; content?: string },
): boolean {
  const rowId = text(row.attr_val_id);
  const rowName = text(row.attr_name);
  const rowContent = text(row.content);
  return (values || []).some((item) => {
    const id = text(item.attr_val_id);
    const name = text(item.attr_name_cn) || text(item.attr_name);
    const content =
      text(item.line_attrval_name_cn) || text(item.line_attrval_name);
    if (rowId && id && rowId === id) {
      return true;
    }
    return rowName === name && rowContent === content && (rowName || rowContent);
  });
}
