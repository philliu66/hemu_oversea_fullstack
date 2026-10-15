import type { ProColumns } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import { Select } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';
import { fetchSupplierOptions } from '@/services/admin/suppliers';
import type { SupplierOption } from '@/types/api';
import { isPlatformRole } from '@/utils/portalScope';

type Props = {
  value?: number;
  onChange?: (value: number | undefined) => void;
  placeholder?: string;
  style?: React.CSSProperties;
  allowClear?: boolean;
  /** false 时不渲染 */
  visible?: boolean;
};

export type SupplierSelectOption = { label: string; value: number };

/** 拉取平台可见供应商下拉（admin=全部，staff=自己维护） */
export async function loadSupplierSelectOptions(): Promise<
  SupplierSelectOption[]
> {
  const items: SupplierOption[] = await fetchSupplierOptions();
  return items.map((item) => ({
    label: `${item.name}（${item.code}）`,
    value: item.id,
  }));
}

/**
 * ProTable 搜索区「供应商」列。必须带 valueType: 'select'，
 * 否则 ProComponents 会落成普通文本输入框。
 */
export function buildPlatformSupplierSearchColumn<DataType>(options: {
  onChange: (value: number | undefined) => void;
}): ProColumns<DataType> {
  return {
    title: '供应商',
    dataIndex: 'supplier_id',
    valueType: 'select',
    hideInTable: true,
    order: 100,
    fieldProps: {
      showSearch: true,
      allowClear: true,
      optionFilterProp: 'label',
      placeholder: '请选择供应商',
      onChange: (value: number | null | undefined) => {
        options.onChange(value == null ? undefined : Number(value));
      },
    },
    request: async () => loadSupplierSelectOptions(),
  };
}

/**
 * 平台角色供应商下拉。供应商角色不渲染。
 * 可用于独立筛选区（非 ProTable 搜索表单）。
 */
const SupplierSelectField: React.FC<Props> = ({
  value,
  onChange,
  placeholder = '请选择供应商',
  style,
  allowClear = true,
  visible,
}) => {
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const role =
    initialState?.currentUser?.access || initialState?.currentUser?.role;
  const show =
    visible ?? (Boolean(access.canPlatform) || isPlatformRole(role));

  const [options, setOptions] = useState<SupplierSelectOption[]>([]);
  const [loading, setLoading] = useState(false);

  const loadOptions = useCallback(async () => {
    setLoading(true);
    try {
      setOptions(await loadSupplierSelectOptions());
    } catch {
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (show) {
      void loadOptions();
    }
  }, [show, loadOptions]);

  if (!show) {
    return null;
  }

  return (
    <Select
      allowClear={allowClear}
      showSearch
      optionFilterProp="label"
      loading={loading}
      options={options}
      value={value}
      onChange={(next) => onChange?.(next)}
      placeholder={placeholder}
      style={{ width: '100%', ...style }}
    />
  );
};

export default SupplierSelectField;
