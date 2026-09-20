import { useIntl } from '@umijs/max';
import { Checkbox, Input, InputNumber, Select, Space } from 'antd';
import React, { useEffect, useState } from 'react';
import type {
  DhCategoryAttrPublic,
  DhCategoryAttrValPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';
import { buildDhImageUrl } from '@/utils/dhImage';

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
      const matchedCustomSlot = !!option && isCustomOption(option);
      const selectedIsCustomPlaceholder =
        isCustomName(item.line_attrval_name) ||
        isCustomName(item.line_attrval_name_cn);

      // 1) 命中分类预置选项，且不是「自定义/其它」槽位 → 普通勾选
      if (option && !matchedCustomSlot && !selectedIsCustomPlaceholder) {
        checked.push(item.attr_val_id);
        return;
      }

      // 2) 未命中预置选项，或命中自定义槽位 → 从 attr_list 反显自定义内容
      if (!allowCustom(attr)) {
        // 不支持自定义时，仍尽量勾选已有选项 id
        if (option) {
          checked.push(item.attr_val_id);
        }
        return;
      }

      draft.customChecked = true;
      const customText = pickCustomText(item);
      const valueAttrName = pickValueAttrName(item);
      if (valueAttrName) {
        customRows.push({
          key: item.attr_val_id || `${valueAttrName}-${customRows.length}`,
          attrName: valueAttrName,
          content: customText,
        });
        return;
      }
      if (customText) {
        fallbackCustomText = customText;
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

  if (options?.singleMode && !hasNamedRows) {
    return (
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={valuePlaceholder}
        allowClear
        style={{ maxWidth: 360, marginTop: 8, width: '100%' }}
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
                <td style={{ ...cellPad, padding: '8px 10px', color: 'rgba(0,0,0,0.65)' }}>
                  {customLabel}
                </td>
                <td style={cellPad}>
                  <Input
                    value={value}
                    placeholder={valuePlaceholder}
                    allowClear
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
}) => {
  const intl = useIntl();
  const [drafts, setDrafts] = useState<Record<string, AttrDraft>>({});

  useEffect(() => {
    setDrafts(buildDrafts(attrs, selectedAttrs));
  }, [attrs, selectedAttrs]);

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

  const patchDraft = (attrId: string, patch: Partial<AttrDraft>) => {
    setDrafts((prev) => ({
      ...prev,
      [attrId]: {
        ...(prev[attrId] || emptyDraft()),
        ...patch,
      },
    }));
  };

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
      },
    );
  };

  return (
    <div>
      {attrs.map((attr) => {
        const draft = drafts[attr.attr_id] || emptyDraft();
        const optionIds = attr.values
          .filter((item) => !isCustomOption(item))
          .map((item) => item.attr_val_id);
        const allChecked =
          optionIds.length > 0 &&
          optionIds.every((id) => draft.checkedValues.includes(id));
        const showPic = attr.style === '2' || attr.style === '3';
        const canCustom = allowCustom(attr);

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
              style={{
                width: 88,
                flexShrink: 0,
                textAlign: 'right',
                paddingTop: 5,
                color: 'rgba(0,0,0,0.88)',
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
                    onChange={(value) =>
                      patchDraft(attr.attr_id, {
                        textValue: value == null ? '' : String(value),
                      })
                    }
                    style={{ maxWidth: 320, width: '100%' }}
                  />
                ) : (
                  <Input
                    value={draft.textValue}
                    onChange={(event) =>
                      patchDraft(attr.attr_id, {
                        textValue: event.target.value,
                      })
                    }
                    style={{ maxWidth: 480 }}
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
                      disabled={draft.customChecked}
                      onChange={(value) =>
                        patchDraft(attr.attr_id, {
                          selectValue: value,
                          customChecked: false,
                        })
                      }
                      options={attr.values
                        .filter((item) => !isCustomOption(item))
                        .map((item) => ({
                          value: item.attr_val_id,
                          label: valueLabel(item),
                        }))}
                      style={{ maxWidth: 320, width: '100%' }}
                    />
                    {canCustom ? (
                      <Checkbox
                        checked={draft.customChecked}
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
                    {attr.values
                      .filter((item) => !isCustomOption(item))
                      .map((item) => {
                        const pic = showPic
                          ? buildDhImageUrl(item.pic_url)
                          : undefined;
                        return (
                          <Checkbox
                            key={item.attr_val_id}
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
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CategoryAttrsFields;
