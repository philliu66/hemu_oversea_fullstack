import { App, Button, Checkbox, Input, InputNumber, Select, Space } from 'antd';
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
import EditableOptionChip from './EditableOptionChip';

const CHANGED_COLOR = '#cf1322';
const CUSTOM_NAME_SET = new Set(['custom', '自定义', 'other', '其它', '其他']);
/** 下拉「自定义」选项的占位 value（当类目值列表中没有显式自定义项时使用） */
const CUSTOM_SELECT_VALUE = '__attr_custom__';
/** 写回 attr_list 时空自定义内容的占位 attr_val_id，用于回流后仍能还原 customChecked */
const CUSTOM_PLACEHOLDER_VAL_ID = 'custom';

type CustomAttrRow = {
  key: string;
  attrName: string;
  content: string;
};

/** 规格属性「输入+添加」产生的多个自定义值 */
type CustomAddedValue = {
  id: string;
  label: string;
};

type AttrDraft = {
  selectValue?: string;
  checkedValues: string[];
  customChecked: boolean;
  customText: string;
  /** 带独立属性名的多行自定义属性（如 Function / Voltage） */
  customRows: CustomAttrRow[];
  /** 规格多选：通过添加按钮写入的多个自定义属性值 */
  customValues: CustomAddedValue[];
  textValue: string;
};

type CategoryAttrsCardProps = {
  attrs: DhCategoryAttrPublic[];
  selectedAttrs?: DhProductSelectedAttrPublic[];
  /** 勾选后展示已选值图片表（规格属性用） */
  showSelectedPics?: boolean;
  /**
   * 规格属性模式：多选自定义改为「输入框 + 添加」，可添加多个自定义属性值
   * （普通类目属性仍用「自定义」勾选 + 表格）
   */
  customAddMode?: boolean;
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

/** 仅识别「自定义/custom」，不含 Other/其他（后者仍作为普通可选项） */
function isExplicitCustomOption(item: DhCategoryAttrValPublic): boolean {
  const names = [item.line_attrval_name, item.line_attrval_name_cn].map((name) =>
    (name || '').trim().toLowerCase(),
  );
  return names.some((name) => name === 'custom' || name === '自定义');
}

function resolveCustomSelectValue(attr: DhCategoryAttrPublic): string {
  return (
    attr.values.find(isExplicitCustomOption)?.attr_val_id || CUSTOM_SELECT_VALUE
  );
}

/** 是否为空自定义占位（仅勾选自定义、尚未填写内容） */
function isCustomPlaceholderValue(item: {
  attr_val_id?: string | null;
  line_attrval_name?: string | null;
  line_attrval_name_cn?: string | null;
}): boolean {
  const id = (item.attr_val_id || '').trim();
  if (id === CUSTOM_PLACEHOLDER_VAL_ID || id === CUSTOM_SELECT_VALUE) {
    return true;
  }
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
  if (
    id &&
    !isCustomName(id) &&
    id !== CUSTOM_PLACEHOLDER_VAL_ID &&
    id !== CUSTOM_SELECT_VALUE &&
    !/^\d+$/.test(id)
  ) {
    return id;
  }
  return '';
}

/** 已选文案是否只是预置选项自身的名称（pushOption 回写后会带上选项名） */
function isOptionOwnLabel(
  option: DhCategoryAttrValPublic,
  customText: string,
): boolean {
  const text = customText.trim();
  if (!text) {
    return true;
  }
  const labels = [
    option.line_attrval_name,
    option.line_attrval_name_cn,
    valueLabel(option),
  ]
    .map((name) => (name || '').trim())
    .filter(Boolean);
  return labels.some((label) => label === text);
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
    customValues: [],
    textValue: '',
  };
}

function buildDrafts(
  attrs: DhCategoryAttrPublic[],
  selectedAttrs?: DhProductSelectedAttrPublic[],
  customAddMode = false,
): Record<string, AttrDraft> {
  const selectedMap = new Map(
    (selectedAttrs || []).map((item) => [String(item.attr_id), item]),
  );
  const next: Record<string, AttrDraft> = {};

  attrs.forEach((attr) => {
    const draft = emptyDraft();
    const optionById = new Map(
      attr.values.map((item) => [String(item.attr_val_id), item]),
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
    const customValues: CustomAddedValue[] = [];
    let fallbackCustomText = '';
    const useAddMode = customAddMode && !isSelectType(attr);

    values.forEach((item) => {
      const valId = String(item.attr_val_id ?? '').trim();
      const option = valId ? optionById.get(valId) : undefined;
      const customText = pickCustomText(item);
      const valueAttrName = pickValueAttrName(item);

      // 规格「添加」模式：未命中预置的值都作为可勾选的自定义属性值
      if (useAddMode && allowCustom(attr) && !option) {
        const label =
          customText ||
          valueAttrName ||
          valId ||
          '';
        if (!label && !valId) {
          return;
        }
        const id = valId || `custom-${label}`;
        if (!customValues.some((row) => row.id === id)) {
          customValues.push({ id, label: label || id });
        }
        if (!checked.includes(id)) {
          checked.push(id);
        }
        return;
      }

      // 带独立属性名的多行自定义（如 Function / Voltage）
      // 注意：详情接口常在预置值上也带回 attrName，不能仅凭有属性名就判自定义；
      // 必须先排除已命中类目预置 attr_val_id 的情况。
      if (allowCustom(attr) && valueAttrName && !option) {
        draft.customChecked = true;
        customRows.push({
          key: valId || `${valueAttrName}-${customRows.length}`,
          attrName: valueAttrName,
          content: customText,
        });
        return;
      }

      // 空自定义占位 / 名称即为「自定义」→ 保持自定义编辑态
      if (allowCustom(attr) && isCustomPlaceholderValue(item) && !option) {
        draft.customChecked = true;
        if (customText) {
          fallbackCustomText = customText;
        }
        return;
      }

      // 命中预置选项：文案等于选项名时当作普通选中；仅当写了不同自定义文案才走自定义
      if (option) {
        if (
          useAddMode ||
          !allowCustom(attr) ||
          isOptionOwnLabel(option, customText)
        ) {
          checked.push(option.attr_val_id);
          return;
        }
        draft.customChecked = true;
        fallbackCustomText = customText;
        return;
      }

      // 未命中预置 → 自定义编辑（或兜底勾选）
      if (!allowCustom(attr)) {
        return;
      }

      draft.customChecked = true;
      if (customText) {
        fallbackCustomText = customText;
      } else if (!isCustomPlaceholderValue(item)) {
        // 兜底：无法识别的已选值仍尽量勾上 id
        if (valId) {
          checked.push(valId);
          draft.customChecked = false;
        }
      }
    });
    draft.customRows = customRows;
    draft.customValues = customValues;
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
  customAddMode = false,
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
      attr.values.map((item) => [String(item.attr_val_id), item]),
    );
    const explicitCustomOption = attr.values.find(isExplicitCustomOption);
    const customOption =
      explicitCustomOption || attr.values.find(isCustomOption);
    const values: DhProductSelectedAttrValPublic[] = [];
    const useAddMode = customAddMode && !isSelectType(attr);

    const pushOption = (valId: string) => {
      const option = optionById.get(String(valId));
      const prevVal = prevByValId.get(String(valId));
      values.push({
        attr_id: attr.attr_id,
        attr_val_id: valId,
        attr_name: null,
        attr_name_cn: null,
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
      allowEmpty = false,
    ) => {
      const trimmed = content.trim();
      const name = (attrName || '').trim();
      if (!trimmed && !name && !allowEmpty) {
        return;
      }
      const valId =
        (key && String(key).trim()) ||
        (trimmed || name
          ? explicitCustomOption?.attr_val_id ||
            customOption?.attr_val_id ||
            (name ? `custom-${name}` : CUSTOM_PLACEHOLDER_VAL_ID)
          : CUSTOM_PLACEHOLDER_VAL_ID);
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

    const pushCustomFromDraft = () => {
      const before = values.length;
      if (draft.customRows.length) {
        draft.customRows.forEach((row) =>
          pushCustom(row.content, row.attrName, row.key),
        );
      } else {
        pushCustom(draft.customText, undefined, undefined, true);
      }
      // 仅勾选自定义、内容全空时仍写占位，避免父级回流冲掉 customChecked
      if (values.length === before) {
        pushCustom('', undefined, undefined, true);
      }
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
        pushCustomFromDraft();
      } else if (draft.selectValue) {
        pushOption(draft.selectValue);
      }
    } else if (useAddMode) {
      const customById = new Map(
        draft.customValues.map((item) => [item.id, item]),
      );
      draft.checkedValues.forEach((id) => {
        if (optionById.has(String(id))) {
          pushOption(id);
          return;
        }
        const custom = customById.get(id);
        const prevVal = prevByValId.get(String(id));
        const label =
          custom?.label ||
          prevVal?.line_attrval_name_cn ||
          prevVal?.line_attrval_name ||
          id;
        pushCustom(String(label), undefined, id);
      });
    } else {
      draft.checkedValues.forEach((id) => pushOption(id));
      if (draft.customChecked) {
        pushCustomFromDraft();
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
    '请输入属性名';
  const valuePlaceholder =
    options?.valuePlaceholder ||
    '请输入属性值';
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
            {'默认参数'}
          </th>
          <th style={headPad}>
            {'自定义内容'}
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
  customAddMode = false,
  storeId,
  disabled = false,
  changedAttrIds,
  onSelectedAttrsChange,
  onValuePicChange,
}) => {
  const changedAttrIdSet = new Set((changedAttrIds || []).map(String));
  const { message } = App.useApp();
  const [drafts, setDrafts] = useState<Record<string, AttrDraft>>({});
  /** 规格「添加」输入框草稿（按 attr_id） */
  const [addInputs, setAddInputs] = useState<Record<string, string>>({});
  /** 正在编辑的自定义值：attrId + valueId */
  const [editingCustom, setEditingCustom] = useState<{
    attrId: string;
    valueId: string;
  }>();
  const [editingCustomName, setEditingCustomName] = useState('');
  const selectedMap = new Map(
    (selectedAttrs || []).map((item) => [String(item.attr_id), item]),
  );
  const onSelectedAttrsChangeRef = React.useRef(onSelectedAttrsChange);
  onSelectedAttrsChangeRef.current = onSelectedAttrsChange;
  const selectedAttrsRef = React.useRef(selectedAttrs);
  selectedAttrsRef.current = selectedAttrs;
  const attrsRef = React.useRef(attrs);
  attrsRef.current = attrs;
  const customAddModeRef = React.useRef(customAddMode);
  customAddModeRef.current = customAddMode;

  useEffect(() => {
    setDrafts((prev) => {
      const built = buildDrafts(attrs, selectedAttrs, customAddMode);
      if (!customAddMode) {
        return built;
      }
      // 规格添加模式：父级 attr_list 只含已勾选项；未勾选的自定义值需从本地草稿合并回来
      const merged: Record<string, AttrDraft> = { ...built };
      attrs.forEach((attr) => {
        if (isSelectType(attr) || isTextType(attr)) {
          return;
        }
        const prevDraft = prev[attr.attr_id] || emptyDraft();
        const nextDraft = built[attr.attr_id] || emptyDraft();
        const byId = new Map(
          nextDraft.customValues.map((item) => [item.id, item]),
        );
        prevDraft.customValues.forEach((item) => {
          if (!byId.has(item.id)) {
            byId.set(item.id, item);
          }
        });
        merged[attr.attr_id] = {
          ...nextDraft,
          customValues: Array.from(byId.values()),
        };
      });
      return merged;
    });
  }, [attrs, selectedAttrs, customAddMode]);

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
          customAddModeRef.current,
        );
        queueMicrotask(() => notify(selected));
      }
      return next;
    });
  };
  const selectAllText = '全选';
  const customLabel = '自定义';
  const placeholder = '请选择';
  const brandCustomPlaceholder = '请输入自定义品牌';
  const customValuePlaceholder = '请输入属性值';
  const addButtonText = '添加';
  const addValuePlaceholder = '请输入自定义属性值';

  const handleAddCustomValue = (attr: DhCategoryAttrPublic) => {
    if (disabled) {
      return;
    }
    const label = (addInputs[attr.attr_id] || '').trim();
    if (!label) {
      message.warning(
        '请输入规格名称',
      );
      return;
    }
    const draft = drafts[attr.attr_id] || emptyDraft();
    const builtinLabels = new Set(
      attr.values.map((item) => valueLabel(item).trim().toLowerCase()),
    );
    const exists =
      draft.customValues.some(
        (item) => item.label.trim().toLowerCase() === label.toLowerCase(),
      ) || builtinLabels.has(label.toLowerCase());
    if (exists) {
      message.warning(
        '规格名称已存在',
      );
      return;
    }
    const id = `custom-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    patchDraft(attr.attr_id, {
      customValues: [...draft.customValues, { id, label }],
      checkedValues: draft.checkedValues.includes(id)
        ? draft.checkedValues
        : [...draft.checkedValues, id],
    });
    setAddInputs((prev) => ({ ...prev, [attr.attr_id]: '' }));
  };

  const handleDeleteCustomValue = (attrId: string, valueId: string) => {
    const draft = drafts[attrId] || emptyDraft();
    patchDraft(attrId, {
      customValues: draft.customValues.filter((row) => row.id !== valueId),
      checkedValues: draft.checkedValues.filter((id) => id !== valueId),
    });
    if (
      editingCustom?.attrId === attrId &&
      editingCustom?.valueId === valueId
    ) {
      setEditingCustom(undefined);
      setEditingCustomName('');
    }
  };

  const startEditCustomValue = (attrId: string, item: CustomAddedValue) => {
    setEditingCustom({ attrId, valueId: item.id });
    setEditingCustomName(item.label);
  };

  const cancelEditCustomValue = () => {
    setEditingCustom(undefined);
    setEditingCustomName('');
  };

  const confirmEditCustomValue = (attr: DhCategoryAttrPublic) => {
    if (!editingCustom || editingCustom.attrId !== attr.attr_id) {
      return;
    }
    const name = editingCustomName.trim();
    if (!name) {
      message.warning(
        '请输入规格名称',
      );
      return;
    }
    const draft = drafts[attr.attr_id] || emptyDraft();
    const builtinLabels = new Set(
      attr.values.map((item) => valueLabel(item).trim().toLowerCase()),
    );
    const duplicate =
      builtinLabels.has(name.toLowerCase()) ||
      draft.customValues.some(
        (item) =>
          item.id !== editingCustom.valueId &&
          item.label.trim().toLowerCase() === name.toLowerCase(),
      );
    if (duplicate) {
      message.warning(
        '规格名称已存在',
      );
      return;
    }
    patchDraft(attr.attr_id, {
      customValues: draft.customValues.map((item) =>
        item.id === editingCustom.valueId ? { ...item, label: name } : item,
      ),
    });
    cancelEditCustomValue();
  };
  const renderAttrCustomEditor = (
    attr: DhCategoryAttrPublic,
    draft: AttrDraft,
  ) => {
    const isBrand = attr.is_brand === '1';
    return renderCustomEditor(
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
        const canCustom = allowCustom(attr);
        const checkboxOptions = attr.values.filter(
          (item) => !(canCustom && isExplicitCustomOption(item)),
        );
        const optionIds = checkboxOptions.map((item) => item.attr_val_id);
        const allChecked =
          optionIds.length > 0 &&
          optionIds.every((id) => draft.checkedValues.includes(id));
        const showPic = attr.style === '2' || attr.style === '3';
        const attrChanged = changedAttrIdSet.has(String(attr.attr_id));
        const customSelectValue = resolveCustomSelectValue(attr);
        const selectOptions = [
          ...attr.values
            .filter((item) => !(canCustom && isExplicitCustomOption(item)))
            .map((item) => ({
              value: item.attr_val_id,
              label: valueLabel(item),
            })),
          ...(canCustom
            ? [{ value: customSelectValue, label: customLabel }]
            : []),
        ];

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
                  <Select
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    placeholder={placeholder}
                    value={
                      draft.customChecked
                        ? customSelectValue
                        : draft.selectValue
                    }
                    disabled={disabled}
                    onChange={(value) => {
                      if (value == null) {
                        patchDraft(attr.attr_id, {
                          selectValue: undefined,
                          customChecked: false,
                        });
                        return;
                      }
                      if (canCustom && value === customSelectValue) {
                        patchDraft(attr.attr_id, {
                          selectValue: undefined,
                          customChecked: true,
                        });
                        return;
                      }
                      patchDraft(attr.attr_id, {
                        selectValue: value,
                        customChecked: false,
                      });
                    }}
                    options={selectOptions}
                    style={{ maxWidth: 480, width: '100%', minWidth: 280 }}
                  />
                  {canCustom && draft.customChecked
                    ? renderAttrCustomEditor(attr, draft)
                    : null}
                </>
              ) : (
                <>
                  {optionIds.length > 0 ? (
                    <div style={{ marginBottom: 8 }}>
                      <Checkbox
                        checked={allChecked}
                        disabled={disabled}
                        indeterminate={
                          !allChecked && draft.checkedValues.length > 0
                        }
                        onChange={(event) => {
                          const customCheckedIds = draft.customValues
                            .map((item) => item.id)
                            .filter((id) =>
                              draft.checkedValues.includes(id),
                            );
                          patchDraft(attr.attr_id, {
                            checkedValues: event.target.checked
                              ? [...optionIds, ...customCheckedIds]
                              : customCheckedIds,
                          });
                        }}
                      >
                        {selectAllText}
                      </Checkbox>
                    </div>
                  ) : null}
                  <Space wrap size={[12, 8]}>
                    {checkboxOptions.map((item) => {
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
                    {customAddMode
                      ? draft.customValues.map((item) => {
                          const isEditing =
                            editingCustom?.attrId === attr.attr_id &&
                            editingCustom?.valueId === item.id;
                          return (
                            <EditableOptionChip
                              key={item.id}
                              label={item.label}
                              checked={draft.checkedValues.includes(item.id)}
                              disabled={disabled}
                              editing={isEditing}
                              editingValue={editingCustomName}
                              onCheckedChange={(checked) => {
                                // 仅控制是否出现在下方已选表，不删除选项本身
                                patchDraft(attr.attr_id, {
                                  checkedValues: checked
                                    ? [...draft.checkedValues, item.id]
                                    : draft.checkedValues.filter(
                                        (id) => id !== item.id,
                                      ),
                                });
                              }}
                              onEditingValueChange={setEditingCustomName}
                              onStartEdit={() =>
                                startEditCustomValue(attr.attr_id, item)
                              }
                              onConfirmEdit={() =>
                                confirmEditCustomValue(attr)
                              }
                              onCancelEdit={cancelEditCustomValue}
                              onDelete={() =>
                                handleDeleteCustomValue(attr.attr_id, item.id)
                              }
                            />
                          );
                        })
                      : null}
                    {!customAddMode && canCustom ? (
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
                  {customAddMode && canCustom && !disabled ? (
                    <div style={{ marginTop: 8 }}>
                      <Space.Compact style={{ maxWidth: 360, width: '100%' }}>
                        <Input
                          value={addInputs[attr.attr_id] || ''}
                          onChange={(event) =>
                            setAddInputs((prev) => ({
                              ...prev,
                              [attr.attr_id]: event.target.value,
                            }))
                          }
                          onPressEnter={() => handleAddCustomValue(attr)}
                          placeholder={addValuePlaceholder}
                        />
                        <Button
                          type="primary"
                          onClick={() => handleAddCustomValue(attr)}
                        >
                          {addButtonText}
                        </Button>
                      </Space.Compact>
                    </div>
                  ) : null}
                  {!customAddMode && canCustom && draft.customChecked
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
                    const customLabelById = new Map(
                      draft.customValues.map((item) => [item.id, item.label]),
                    );
                    const hasPicFeature =
                      showPic ||
                      attr.values.some((item) => Boolean(item.pic_url)) ||
                      (selected?.values || []).some((item) =>
                        Boolean(item.pic_url),
                      ) ||
                      customAddMode;
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
                            customLabelById.get(String(id)) ||
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
                          maxWidth: 480,
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
                                width: 120,
                              }}
                            >
                              {'自定义图片（无图可忽略）'}
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
                                    width: 160,
                                  }}
                                >
                                  <Space size={8} wrap>
                                    <span>{item.label}</span>
                                    {!disabled ? (
                                      <Button
                                        type="link"
                                        size="small"
                                        danger
                                        style={{ padding: 0, height: 'auto' }}
                                        onClick={() => {
                                          if (isSelectType(attr)) {
                                            patchDraft(attr.attr_id, {
                                              selectValue: undefined,
                                              ...(item.id ===
                                                CUSTOM_SELECT_VALUE ||
                                              draft.selectValue ===
                                                CUSTOM_SELECT_VALUE
                                                ? { customChecked: false }
                                                : null),
                                            });
                                            return;
                                          }
                                          patchDraft(attr.attr_id, {
                                            checkedValues:
                                              draft.checkedValues.filter(
                                                (id) => id !== item.id,
                                              ),
                                          });
                                        }}
                                      >
                                        {'删除'}
                                      </Button>
                                    ) : null}
                                  </Space>
                                </td>
                                <td
                                  style={{
                                    border: '1px solid #d9d9d9',
                                    padding: '8px 10px',
                                    verticalAlign: 'middle',
                                    width: 120,
                                    textAlign: 'center',
                                  }}
                                >
                                  <div
                                    style={{
                                      display: 'inline-flex',
                                      justifyContent: 'center',
                                      alignItems: 'center',
                                    }}
                                  >
                                    <DhgateAttrPicUpload
                                      storeId={storeId}
                                      value={item.picUrl}
                                      disabled={disabled}
                                      compact
                                      onChange={(picUrl) =>
                                        onValuePicChange?.(
                                          attr.attr_id,
                                          item.id,
                                          picUrl,
                                        )
                                      }
                                    />
                                  </div>
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
