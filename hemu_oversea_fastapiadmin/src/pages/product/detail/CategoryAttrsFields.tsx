import { useIntl } from '@umijs/max';
import { Checkbox, Input, InputNumber, Select, Space } from 'antd';
import React, { useEffect, useState } from 'react';
import type {
  DhCategoryAttrPublic,
  DhCategoryAttrValPublic,
  DhProductSelectedAttrPublic,
  DhProductSelectedAttrValPublic,
} from '@/types/api';
import { buildDhImageUrl } from '@/utils/dhImage';
import './changedHighlight.css';
import DhgateAttrPicUpload from './DhgateAttrPicUpload';

const CHANGED_COLOR = '#cf1322';
const CUSTOM_NAME_SET = new Set(['custom', '自定义', 'other', '其它', '其他']);

type CustomAttrRow = {
  key: string;
  attrName: string;
  content: string;
};

type AttrDraft = {
  selectValue?: string;
  checkedValues: string[];
  customChecked: boolean;
  customText: string;
  /** 带独立属性名的多行自定义属性（如 Function / Voltage） */
  customRows: CustomAttrRow[];
  textValue: string;
};

type CategoryAttrsCardProps = {
  attrs: DhCategoryAttrPublic[];
  selectedAttrs?: DhProductSelectedAttrPublic[];
  /** 勾选后展示已选值图片表（规格属性用） */
  showSelectedPics?: boolean;
  storeId?: number;
  /** 只读（查看详情） */
  disabled?: boolean;
  /** 相对种子有变更的属性 ID，标签标红 */
  changedAttrIds?: string[];
  /** 属性勾选/填写变更后回写（本组件管理的属性子集） */
  onSelectedAttrsChange?: (next: DhProductSelectedAttrPublic[]) => void;
  /** 属性值图片变更（写入 / 覆盖 pic_url） */
  onValuePicChange?: (
    attrId: string,
    attrValId: string,
    picUrl: string | null,
  ) => void;
};

function attrLabel(attr: DhCategoryAttrPublic): string {
  return (
    attr.line_attr_name_cn?.trim() ||
    attr.line_attr_name?.trim() ||
    attr.attr_id
  );
}

function valueLabel(item: DhCategoryAttrValPublic): string {
  const en = item.line_attrval_name?.trim() || '';
  const cn = item.line_attrval_name_cn?.trim() || '';
  if (en && cn && en !== cn) {
    return `${en}(${cn})`;
  }
  return en || cn || item.attr_val_id;
}

function allowCustom(attr: DhCategoryAttrPublic): boolean {
  return attr.isother === '1' || attr.defined === '1';
}

function isSelectType(attr: DhCategoryAttrPublic): boolean {
  return attr.type === '2' || attr.is_brand === '1';
}

function isTextType(attr: DhCategoryAttrPublic): boolean {
  return attr.type === '4' || attr.type === '5';
}

function isCustomName(name?: string | null): boolean {
  return CUSTOM_NAME_SET.has((name || '').trim().toLowerCase());
}

function isCustomOption(item: DhCategoryAttrValPublic): boolean {
  return (
    isCustomName(item.line_attrval_name) ||
    isCustomName(item.line_attrval_name_cn)
  );
}

/** 从详情 attr_list 的属性值中解析可展示的自定义文案 */
function pickCustomText(item: {
  attr_val_id?: string;
  line_attrval_name?: string | null;
  line_attrval_name_cn?: string | null;
}): string {
  const candidates = [
    item.line_attrval_name,
    item.line_attrval_name_cn,
  ].filter((text): text is string => {
    const trimmed = text?.trim();
    return !!trimmed && !isCustomName(trimmed);
  });
  if (candidates.length > 0) {
    return candidates[0].trim();
  }
  // attr_val_id 若不是占位名，也可能是自定义内容标识
  const id = item.attr_val_id?.trim();
  if (id && !isCustomName(id) && !/^\d+$/.test(id)) {
    return id;
  }
  return '';
}

/** 值级属性名（自定义属性每一行的参数名） */
function pickValueAttrName(item: {
  attr_name?: string | null;
  attr_name_cn?: string | null;
}): string {
  return (
    item.attr_name_cn?.trim() ||
    item.attr_name?.trim() ||
    ''
  );
}

function emptyDraft(): AttrDraft {
  return {
    checkedValues: [],
    customChecked: false,
    customText: '',
    customRows: [],
    textValue: '',
  };
}

function buildDrafts(
  attrs: DhCategoryAttrPublic[],
  selectedAttrs?: DhProductSelectedAttrPublic[],
): Record<string, AttrDraft> {
  const selectedMap = new Map(
    (selectedAttrs || []).map((item) => [String(item.attr_id), item]),
  );
  const next: Record<string, AttrDraft> = {};

  attrs.forEach((attr) => {
    const draft = emptyDraft();
    const optionById = new Map(
      attr.values.map((item) => [item.attr_val_id, item]),
    );
    const selected = selectedMap.get(String(attr.attr_id));
    const values = selected?.values || [];

    if (isTextType(attr)) {
      draft.textValue =
        values[0]?.line_attrval_name_cn ||
        values[0]?.line_attrval_name ||
        values[0]?.attr_val_id ||
        '';
      next[attr.attr_id] = draft;
      return;
    }

    const checked: string[] = [];
    const customRows: CustomAttrRow[] = [];
    let fallbackCustomText = '';
    values.forEach((item) => {
      const option = optionById.get(item.attr_val_id);
      const customText = pickCustomText(item);
      const valueAttrName = pickValueAttrName(item);
      const selectedIsCustomPlaceholder =
        isCustomName(item.line_attrval_name) ||
        isCustomName(item.line_attrval_name_cn);

      // 带独立属性名的多行自定义（如 Function / Voltage）
      if (allowCustom(attr) && valueAttrName) {
        draft.customChecked = true;
        customRows.push({
          key: item.attr_val_id || `${valueAttrName}-${customRows.length}`,
          attrName: valueAttrName,
          content: customText,
        });
        return;
      }

      // 命中预置选项（含「其他/Others」）：无额外自定义文案时当作普通选项选中
      if (option && !customText) {
        checked.push(item.attr_val_id);
        return;
      }

      // 未命中预置，或命中「其他」槽位但写了自定义文案 → 自定义编辑
      if (!allowCustom(attr)) {
        if (option) {
          checked.push(item.attr_val_id);
        }
        return;
      }

      draft.customChecked = true;
      if (customText) {
        fallbackCustomText = customText;
      } else if (!option && !selectedIsCustomPlaceholder) {
        // 兜底：无法识别的已选值仍尽量勾上 id
        if (item.attr_val_id) {
          checked.push(item.attr_val_id);
          draft.customChecked = false;
        }
      }
    });
    draft.customRows = customRows;
    // 无独立属性名时，退回单行「自定义」文案（取最后一条有效内容）
    if (customRows.length === 0 && fallbackCustomText) {
      draft.customText = fallbackCustomText;
    }

    if (isSelectType(attr)) {
      draft.selectValue = checked[0];
    } else {
      draft.checkedValues = checked;
    }
    next[attr.attr_id] = draft;
  });

  return next;
}

/** draft → 本组件管理的属性子集（用于写回 detail.attr_list） */
function draftsToSelectedAttrs(
  attrs: DhCategoryAttrPublic[],
  drafts: Record<string, AttrDraft>,
  previousSelected?: DhProductSelectedAttrPublic[],
): DhProductSelectedAttrPublic[] {
  const prevMap = new Map(
    (previousSelected || []).map((item) => [String(item.attr_id), item]),
  );
  const result: DhProductSelectedAttrPublic[] = [];

  for (const attr of attrs) {
    const draft = drafts[attr.attr_id] || emptyDraft();
    const prev = prevMap.get(String(attr.attr_id));
    const prevByValId = new Map(
      (prev?.values || [])
        .filter((item) => item.attr_val_id != null && item.attr_val_id !== '')
        .map((item) => [String(item.attr_val_id), item]),
    );
    const optionById = new Map(
      attr.values.map((item) => [item.attr_val_id, item]),
    );
    const customOption = attr.values.find(isCustomOption);
    const values: DhProductSelectedAttrValPublic[] = [];

    const pushOption = (valId: string) => {
      const option = optionById.get(valId);
      const prevVal = prevByValId.get(String(valId));
      values.push({
        attr_id: attr.attr_id,
        attr_val_id: valId,
        attr_name: prevVal?.attr_name ?? null,
        attr_name_cn: prevVal?.attr_name_cn ?? null,
        line_attrval_name:
          option?.line_attrval_name ?? prevVal?.line_attrval_name ?? null,
        line_attrval_name_cn:
          option?.line_attrval_name_cn ?? prevVal?.line_attrval_name_cn ?? null,
        pic_url: prevVal?.pic_url ?? option?.pic_url ?? null,
        brand_id: prevVal?.brand_id ?? null,
      });
    };

    const pushCustom = (
      content: string,
      attrName?: string,
      key?: string,
    ) => {
      const trimmed = content.trim();
      const name = (attrName || '').trim();
      if (!trimmed && !name) {
        return;
      }
      const valId =
        (key && String(key).trim()) ||
        customOption?.attr_val_id ||
        (name ? `custom-${name}` : 'custom');
      const prevVal = prevByValId.get(String(valId));
      values.push({
        attr_id: attr.attr_id,
        attr_val_id: valId,
        attr_name: name || prevVal?.attr_name || null,
        attr_name_cn: name || prevVal?.attr_name_cn || null,
        line_attrval_name: trimmed || null,
        line_attrval_name_cn: trimmed || null,
        pic_url: prevVal?.pic_url ?? null,
        brand_id: prevVal?.brand_id ?? null,
      });
    };

    if (isTextType(attr)) {
      const text = draft.textValue.trim();
      if (text) {
        const prevVal = prev?.values?.[0];
        values.push({
          attr_id: attr.attr_id,
          attr_val_id: prevVal?.attr_val_id || text,
          attr_name: null,
          attr_name_cn: null,
          line_attrval_name: text,
          line_attrval_name_cn: text,
          pic_url: prevVal?.pic_url ?? null,
          brand_id: prevVal?.brand_id ?? null,
        });
      }
    } else if (isSelectType(attr)) {
      if (draft.customChecked) {
        if (draft.customRows.length) {
          draft.customRows.forEach((row) =>
            pushCustom(row.content, row.attrName, row.key),
          );
        } else {
          pushCustom(draft.customText);
        }
      } else if (draft.selectValue) {
        pushOption(draft.selectValue);
      }
    } else {
      draft.checkedValues.forEach((id) => pushOption(id));
      if (draft.customChecked) {
        if (draft.customRows.length) {
          draft.customRows.forEach((row) =>
            pushCustom(row.content, row.attrName, row.key),
          );
        } else {
          pushCustom(draft.customText);
        }
      }
    }

    // 无值时：规格属性保留空壳以免 UI 消失；普通类目属性则省略
    if (!values.length) {
      if (String(prev?.is_price_attr) === '1') {
        result.push({
          attr_id: attr.attr_id,
          attr_name: prev?.attr_name ?? attr.line_attr_name ?? null,
          attr_name_cn: prev?.attr_name_cn ?? attr.line_attr_name_cn ?? null,
          is_brand: attr.is_brand ?? prev?.is_brand ?? null,
          is_price_attr: '1',
          values: [],
        });
      }
      continue;
    }

    result.push({
      attr_id: attr.attr_id,
      attr_name: prev?.attr_name ?? attr.line_attr_name ?? null,
      attr_name_cn: prev?.attr_name_cn ?? attr.line_attr_name_cn ?? null,
      is_brand: attr.is_brand ?? prev?.is_brand ?? null,
      is_price_attr: prev?.is_price_attr ?? null,
      values,
    });
  }

  return result;
}

function renderCustomEditor(
  intl: ReturnType<typeof useIntl>,
  customLabel: string,
  value: string,
  onChange: (value: string) => void,
  rows?: CustomAttrRow[],
  onRowsChange?: (rows: CustomAttrRow[]) => void,
  options?: {
    /** 品牌等单字段自定义：只渲染一个明显输入框 */
    singleMode?: boolean;
    namePlaceholder?: string;
    valuePlaceholder?: string;
    disabled?: boolean;
  },
) {
  const hasNamedRows = (rows?.length || 0) > 0;
  const namePlaceholder =
    options?.namePlaceholder ||
    intl.formatMessage({
      id: 'pages.product.detail.attrsCustomNamePlaceholder',
      defaultMessage: '请输入属性名',
    });
  const valuePlaceholder =
    options?.valuePlaceholder ||
    intl.formatMessage({
      id: 'pages.product.detail.attrsCustomValuePlaceholder',
      defaultMessage: '请输入属性值',
    });
  const editorDisabled = Boolean(options?.disabled);

  if (options?.singleMode && !hasNamedRows) {
    return (
      <Input
        value={value}
        disabled={editorDisabled}
        onChange={(event) => onChange(event.target.value)}
        placeholder={valuePlaceholder}
        allowClear
        style={{ maxWidth: 480, marginTop: 8, width: '100%' }}
      />
    );
  }

  const cellPad = { border: '1px solid #d9d9d9', padding: 6 } as const;
  const headPad = {
    border: '1px solid #d9d9d9',
    background: '#fafafa',
    padding: '6px 10px',
    fontWeight: 500,
    textAlign: 'left' as const,
  };

  return (
    <table
      style={{
        marginTop: 8,
        borderCollapse: 'collapse',
        maxWidth: 640,
        width: '100%',
        fontSize: 13,
      }}
    >
      <thead>
        <tr>
          <th style={{ ...headPad, width: 200 }}>
            {intl.formatMessage({
              id: 'pages.product.detail.attrsCustomParam',
              defaultMessage: '默认参数',
            })}
          </th>
          <th style={headPad}>
            {intl.formatMessage({
              id: 'pages.product.detail.attrsCustomContent',
              defaultMessage: '自定义内容',
            })}
          </th>
        </tr>
      </thead>
      <tbody>
        {hasNamedRows
          ? rows!.map((row, index) => (
              <tr key={row.key}>
                <td style={cellPad}>
                  <Input
                    value={row.attrName}
                    placeholder={namePlaceholder}
                    allowClear
                    disabled={editorDisabled}
                    onChange={(event) => {
                      if (!onRowsChange || !rows) {
                        return;
                      }
                      const next = rows.map((item, i) =>
                        i === index
                          ? { ...item, attrName: event.target.value }
                          : item,
                      );
                      onRowsChange(next);
                    }}
                  />
                </td>
                <td style={cellPad}>
                  <Input
                    value={row.content}
                    placeholder={valuePlaceholder}
                    allowClear
                    disabled={editorDisabled}
                    onChange={(event) => {
                      if (!onRowsChange || !rows) {
                        return;
                      }
                      const next = rows.map((item, i) =>
                        i === index
                          ? { ...item, content: event.target.value }
                          : item,
                      );
                      onRowsChange(next);
                    }}
                  />
                </td>
              </tr>
            ))
          : (
              <tr>
                <td
                  style={{
                    ...cellPad,
                    padding: '8px 10px',
                    color: 'rgba(0,0,0,0.65)',
                  }}
                >
                  {customLabel}
                </td>
                <td style={cellPad}>
                  <Input
                    value={value}
                    placeholder={valuePlaceholder}
                    allowClear
                    disabled={editorDisabled}
                    onChange={(event) => onChange(event.target.value)}
                  />
                </td>
              </tr>
            )}
      </tbody>
    </table>
  );
}

const CategoryAttrsFields: React.FC<CategoryAttrsCardProps> = ({
  attrs,
  selectedAttrs,
  showSelectedPics = false,
  storeId,
  disabled = false,
  changedAttrIds,
  onSelectedAttrsChange,
  onValuePicChange,
}) => {
  const changedAttrIdSet = new Set((changedAttrIds || []).map(String));
  const intl = useIntl();
  const [drafts, setDrafts] = useState<Record<string, AttrDraft>>({});
  const selectedMap = new Map(
    (selectedAttrs || []).map((item) => [String(item.attr_id), item]),
  );
  const onSelectedAttrsChangeRef = React.useRef(onSelectedAttrsChange);
  onSelectedAttrsChangeRef.current = onSelectedAttrsChange;
  const selectedAttrsRef = React.useRef(selectedAttrs);
  selectedAttrsRef.current = selectedAttrs;
  const attrsRef = React.useRef(attrs);
  attrsRef.current = attrs;

  useEffect(() => {
    setDrafts(buildDrafts(attrs, selectedAttrs));
  }, [attrs, selectedAttrs]);

  const patchDraft = (attrId: string, patch: Partial<AttrDraft>) => {
    if (disabled) {
      return;
    }
    setDrafts((prev) => {
      const next = {
        ...prev,
        [attrId]: {
          ...(prev[attrId] || emptyDraft()),
          ...patch,
        },
      };
      const notify = onSelectedAttrsChangeRef.current;
      if (notify) {
        const selected = draftsToSelectedAttrs(
          attrsRef.current,
          next,
          selectedAttrsRef.current,
        );
        queueMicrotask(() => notify(selected));
      }
      return next;
    });
  };
  const selectAllText = intl.formatMessage({
    id: 'pages.product.detail.attrsSelectAll',
    defaultMessage: '全选',
  });
  const customLabel = intl.formatMessage({
    id: 'pages.product.detail.attrsCustom',
    defaultMessage: '自定义',
  });
  const placeholder = intl.formatMessage({
    id: 'pages.product.detail.attrsPlaceholder',
    defaultMessage: '请选择',
  });
  const brandCustomPlaceholder = intl.formatMessage({
    id: 'pages.product.detail.attrsBrandCustomPlaceholder',
    defaultMessage: '请输入自定义品牌',
  });
  const customValuePlaceholder = intl.formatMessage({
    id: 'pages.product.detail.attrsCustomValuePlaceholder',
    defaultMessage: '请输入属性值',
  });

  const renderAttrCustomEditor = (
    attr: DhCategoryAttrPublic,
    draft: AttrDraft,
  ) => {
    const isBrand = attr.is_brand === '1';
    return renderCustomEditor(
      intl,
      customLabel,
      draft.customText,
      (value) => patchDraft(attr.attr_id, { customText: value }),
      draft.customRows,
      (rows) => patchDraft(attr.attr_id, { customRows: rows }),
      {
        singleMode: isBrand,
        valuePlaceholder: isBrand
          ? brandCustomPlaceholder
          : customValuePlaceholder,
        disabled,
      },
    );
  };

  return (
    <div>
      {attrs.map((attr) => {
        const draft = drafts[attr.attr_id] || emptyDraft();
        const optionIds = attr.values.map((item) => item.attr_val_id);
        const allChecked =
          optionIds.length > 0 &&
          optionIds.every((id) => draft.checkedValues.includes(id));
        const showPic = attr.style === '2' || attr.style === '3';
        const canCustom = allowCustom(attr);
        const attrChanged = changedAttrIdSet.has(String(attr.attr_id));

        return (
          <div
            key={attr.attr_id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              marginBottom: 16,
              columnGap: 12,
            }}
          >
            <div
              className={attrChanged ? 'hm-changed-text' : undefined}
              style={{
                width: 88,
                flexShrink: 0,
                textAlign: 'left',
                paddingTop: 5,
                color: attrChanged ? CHANGED_COLOR : 'rgba(0,0,0,0.88)',
                lineHeight: '22px',
              }}
            >
              {attr.required === '1' ? (
                <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>
              ) : null}
              {attrLabel(attr)}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              {isTextType(attr) ? (
                attr.type === '5' ? (
                  <InputNumber
                    value={(() => {
                      if (draft.textValue === '') {
                        return undefined;
                      }
                      const num = Number(draft.textValue);
                      return Number.isNaN(num) ? undefined : num;
                    })()}
                    disabled={disabled}
                    onChange={(value) =>
                      patchDraft(attr.attr_id, {
                        textValue: value == null ? '' : String(value),
                      })
                    }
                    style={{ maxWidth: 420, width: '100%' }}
                  />
                ) : (
                  <Input
                    value={draft.textValue}
                    disabled={disabled}
                    onChange={(event) =>
                      patchDraft(attr.attr_id, {
                        textValue: event.target.value,
                      })
                    }
                    style={{ maxWidth: 560 }}
                  />
                )
              ) : isSelectType(attr) ? (
                <>
                  <Space wrap size={[12, 8]} style={{ width: '100%' }}>
                    <Select
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      placeholder={placeholder}
                      value={draft.customChecked ? undefined : draft.selectValue}
                      disabled={disabled || draft.customChecked}
                      onChange={(value) =>
                        patchDraft(attr.attr_id, {
                          selectValue: value,
                          customChecked: false,
                        })
                      }
                      options={attr.values.map((item) => ({
                        value: item.attr_val_id,
                        label: valueLabel(item),
                      }))}
                      style={{ maxWidth: 480, width: '100%', minWidth: 280 }}
                    />
                    {canCustom ? (
                      <Checkbox
                        checked={draft.customChecked}
                        disabled={disabled}
                        onChange={(event) =>
                          patchDraft(attr.attr_id, {
                            customChecked: event.target.checked,
                            ...(event.target.checked
                              ? { selectValue: undefined }
                              : {}),
                          })
                        }
                      >
                        {customLabel}
                      </Checkbox>
                    ) : null}
                  </Space>
                  {canCustom && draft.customChecked
                    ? renderAttrCustomEditor(attr, draft)
                    : null}
                </>
              ) : (
                <>
                  <Space wrap size={[12, 8]}>
                    {optionIds.length > 0 ? (
                      <Checkbox
                        checked={allChecked}
                        disabled={disabled}
                        indeterminate={
                          !allChecked && draft.checkedValues.length > 0
                        }
                        onChange={(event) =>
                          patchDraft(attr.attr_id, {
                            checkedValues: event.target.checked
                              ? optionIds
                              : [],
                          })
                        }
                      >
                        {selectAllText}
                      </Checkbox>
                    ) : null}
                    {attr.values.map((item) => {
                        const pic = showPic
                          ? buildDhImageUrl(item.pic_url)
                          : undefined;
                        return (
                          <Checkbox
                            key={item.attr_val_id}
                            disabled={disabled}
                            checked={draft.checkedValues.includes(
                              item.attr_val_id,
                            )}
                            onChange={(event) => {
                              const checked = event.target.checked
                                ? [...draft.checkedValues, item.attr_val_id]
                                : draft.checkedValues.filter(
                                    (id) => id !== item.attr_val_id,
                                  );
                              patchDraft(attr.attr_id, {
                                checkedValues: checked,
                              });
                            }}
                          >
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 6,
                              }}
                            >
                              {pic ? (
                                <img
                                  src={pic}
                                  alt=""
                                  width={16}
                                  height={16}
                                  style={{
                                    objectFit: 'cover',
                                    borderRadius: 2,
                                  }}
                                />
                              ) : null}
                              {valueLabel(item)}
                            </span>
                          </Checkbox>
                        );
                      })}
                    {canCustom ? (
                      <Checkbox
                        checked={draft.customChecked}
                        disabled={disabled}
                        onChange={(event) =>
                          patchDraft(attr.attr_id, {
                            customChecked: event.target.checked,
                          })
                        }
                      >
                        {customLabel}
                      </Checkbox>
                    ) : null}
                  </Space>
                  {canCustom && draft.customChecked
                    ? renderAttrCustomEditor(attr, draft)
                    : null}
                </>
              )}
              {showSelectedPics
                ? (() => {
                    const selected = selectedMap.get(String(attr.attr_id));
                    const selectedById = new Map(
                      (selected?.values || []).map((item) => [
                        String(item.attr_val_id),
                        item,
                      ]),
                    );
                    const categoryById = new Map(
                      attr.values.map((item) => [
                        String(item.attr_val_id),
                        item,
                      ]),
                    );
                    const hasPicFeature =
                      showPic ||
                      attr.values.some((item) => Boolean(item.pic_url)) ||
                      (selected?.values || []).some((item) =>
                        Boolean(item.pic_url),
                      );
                    if (!hasPicFeature) {
                      return null;
                    }

                    const selectedIds: string[] = [];
                    if (isSelectType(attr)) {
                      if (draft.selectValue) {
                        selectedIds.push(draft.selectValue);
                      }
                    } else if (!isTextType(attr)) {
                      selectedIds.push(...draft.checkedValues);
                    }
                    if (!selectedIds.length) {
                      return null;
                    }

                    const rows = selectedIds.map((id) => {
                      const fromSelected = selectedById.get(String(id));
                      const fromCategory = categoryById.get(String(id));
                      const en =
                        fromSelected?.line_attrval_name?.trim() ||
                        fromCategory?.line_attrval_name?.trim() ||
                        '';
                      const cn =
                        fromSelected?.line_attrval_name_cn?.trim() ||
                        fromCategory?.line_attrval_name_cn?.trim() ||
                        '';
                      const label =
                        en && cn && en !== cn
                          ? `${en}(${cn})`
                          : en ||
                            cn ||
                            (fromCategory ? valueLabel(fromCategory) : id);
                      const picUrl =
                        fromSelected?.pic_url ||
                        fromCategory?.pic_url ||
                        null;
                      return { id, label, picUrl };
                    });

                    const title =
                      selected?.attr_name_cn?.trim() ||
                      selected?.attr_name?.trim() ||
                      attrLabel(attr);
                    return (
                      <table
                        style={{
                          marginTop: 12,
                          borderCollapse: 'collapse',
                          width: '100%',
                          maxWidth: 720,
                          fontSize: 13,
                        }}
                      >
                        <thead>
                          <tr>
                            <th
                              style={{
                                border: '1px solid #d9d9d9',
                                background: '#fafafa',
                                padding: '6px 10px',
                                textAlign: 'left',
                                fontWeight: 500,
                                width: 160,
                              }}
                            >
                              {title}
                            </th>
                            <th
                              style={{
                                border: '1px solid #d9d9d9',
                                background: '#fafafa',
                                padding: '6px 10px',
                                textAlign: 'left',
                                fontWeight: 500,
                              }}
                            >
                              {intl.formatMessage({
                                id: 'pages.product.detail.specAttrs.customPic',
                                defaultMessage: '自定义图片（无图可忽略）',
                              })}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((item) => {
                            return (
                              <tr key={item.id}>
                                <td
                                  style={{
                                    border: '1px solid #d9d9d9',
                                    padding: '8px 10px',
                                    verticalAlign: 'middle',
                                  }}
                                >
                                  {item.label}
                                </td>
                                <td
                                  style={{
                                    border: '1px solid #d9d9d9',
                                    padding: '8px 10px',
                                    verticalAlign: 'middle',
                                  }}
                                >
                                  <DhgateAttrPicUpload
                                    storeId={storeId}
                                    value={item.picUrl}
                                    disabled={disabled}
                                    onChange={(picUrl) =>
                                      onValuePicChange?.(
                                        attr.attr_id,
                                        item.id,
                                        picUrl,
                                      )
                                    }
                                  />
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    );
                  })()
                : null}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CategoryAttrsFields;
