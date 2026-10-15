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

/**
 * 平台角色供应商下拉。供应商角色不渲染。
 * 可用于 ProTable renderFormItem 或独立筛选区。
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

  const [options, setOptions] = useState<
    { label: string; value: number }[]
  >([]);
  const [loading, setLoading] = useState(false);

  const loadOptions = useCallback(async () => {
    setLoading(true);
    try {
      const items: SupplierOption[] = await fetchSupplierOptions();
      setOptions(
        items.map((item) => ({
          label: `${item.name}（${item.code}）`,
          value: item.id,
        })),
      );
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
