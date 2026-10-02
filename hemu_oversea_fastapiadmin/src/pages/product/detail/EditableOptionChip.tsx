import {
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { Checkbox, Input } from 'antd';
import React from 'react';

type EditableOptionChipProps = {
  label: string;
  checked: boolean;
  disabled?: boolean;
  editing?: boolean;
  editingValue?: string;
  onCheckedChange?: (checked: boolean) => void;
  onEditingValueChange?: (value: string) => void;
  onStartEdit?: () => void;
  onConfirmEdit?: () => void;
  onCancelEdit?: () => void;
  onDelete?: () => void;
};

/**
 * 规格自定义值 / 自定义规格共用的「可选 + 可编辑 + 可删除」标签。
 * 勾选仅表示是否选中，删除由删除图标负责。
 */
const EditableOptionChip: React.FC<EditableOptionChipProps> = ({
  label,
  checked,
  disabled = false,
  editing = false,
  editingValue = '',
  onCheckedChange,
  onEditingValueChange,
  onStartEdit,
  onConfirmEdit,
  onCancelEdit,
  onDelete,
}) => {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '2px 8px',
        border: '1px solid #d9d9d9',
        borderRadius: 4,
        background: '#fafafa',
      }}
    >
      <Checkbox
        checked={checked}
        disabled={disabled}
        onChange={(event) => onCheckedChange?.(event.target.checked)}
      />
      {editing ? (
        <Input
          size="small"
          value={editingValue}
          disabled={disabled}
          onChange={(event) => onEditingValueChange?.(event.target.value)}
          onPressEnter={() => onConfirmEdit?.()}
          style={{ width: 140 }}
        />
      ) : (
        <span>{label || '-'}</span>
      )}
      {!disabled && editing ? (
        <>
          <CheckOutlined
            style={{ color: '#1677ff', cursor: 'pointer' }}
            onClick={() => onConfirmEdit?.()}
          />
          <CloseOutlined
            style={{ color: 'rgba(0,0,0,0.45)', cursor: 'pointer' }}
            onClick={() => onCancelEdit?.()}
          />
        </>
      ) : null}
      {!disabled && !editing ? (
        <>
          <EditOutlined
            style={{ color: 'rgba(0,0,0,0.45)', cursor: 'pointer' }}
            title={'编辑'}
            onClick={() => onStartEdit?.()}
          />
          <DeleteOutlined
            style={{ color: 'rgba(0,0,0,0.45)', cursor: 'pointer' }}
            title={'删除'}
            onClick={() => onDelete?.()}
          />
        </>
      ) : null}
    </span>
  );
};

export default EditableOptionChip;
