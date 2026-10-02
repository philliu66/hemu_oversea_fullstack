import { Checkbox, InputNumber, Space, Typography } from 'antd';
import React, { useMemo } from 'react';
import type { DhItemWeightRangePublic } from '@/types/api';

type PackageInfoFieldsProps = {
  grossWeight?: string | number | null;
  length?: string | number | null;
  width?: string | number | null;
  height?: string | number | null;
  weightRange?: DhItemWeightRangePublic | null;
  disabled?: boolean;
  onGrossWeightChange?: (value: number | null) => void;
  onLengthChange?: (value: number | null) => void;
  onWidthChange?: (value: number | null) => void;
  onHeightChange?: (value: number | null) => void;
  onWeightRangeChange?: (value: DhItemWeightRangePublic | null) => void;
};

function toNumber(value: string | number | null | undefined): number | null {
  if (value == null || value === '') {
    return null;
  }
  const num = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(num) ? num : null;
}

function hasWeightRange(range?: DhItemWeightRangePublic | null): boolean {
  if (!range) {
    return false;
  }
  return (
    range.base_qt != null ||
    range.step_qt != null ||
    range.step_weight != null
  );
}

/**
 * 包装信息：对应详情 itemPackage
 * - gross_weight / length / width / height
 * - item_weight_range（itemWeigthRange）：产品计重阶梯
 */
const PackageInfoFields: React.FC<PackageInfoFieldsProps> = ({
  grossWeight,
  length,
  width,
  height,
  weightRange,
  disabled = false,
  onGrossWeightChange,
  onLengthChange,
  onWidthChange,
  onHeightChange,
  onWeightRangeChange,
}) => {
  const ladderEnabled = hasWeightRange(weightRange);

  const volume = useMemo(() => {
    const l = toNumber(length);
    const w = toNumber(width);
    const h = toNumber(height);
    if (l == null || w == null || h == null) {
      return null;
    }
    const result = l * w * h;
    return Number.isFinite(result) ? result : null;
  }, [length, width, height]);

  const labelStyle: React.CSSProperties = {
    width: 110,
    flex: '0 0 110px',
    lineHeight: '32px',
    textAlign: 'right',
    paddingRight: 8,
    color: 'rgba(0,0,0,0.88)',
  };

  const patchRange = (patch: Partial<DhItemWeightRangePublic>) => {
    if (disabled) {
      return;
    }
    onWeightRangeChange?.({
      base_qt: weightRange?.base_qt ?? null,
      step_qt: weightRange?.step_qt ?? null,
      step_weight: weightRange?.step_weight ?? null,
      ...patch,
    });
  };

  return (
    <div style={{ maxWidth: 900 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          marginBottom: 16,
          flexWrap: 'wrap',
          rowGap: 8,
        }}
      >
        <div style={labelStyle}>
          <Typography.Text type="danger">*</Typography.Text>
          {'包装后重量'}
          :
        </div>
        <Space wrap size={8} align="center" style={{ flex: 1, minWidth: 0 }}>
          <InputNumber
            min={0}
            step={0.01}
            disabled={disabled}
            value={toNumber(grossWeight) ?? undefined}
            style={{ width: 120 }}
            onChange={(value) =>
              onGrossWeightChange?.(typeof value === 'number' ? value : null)
            }
          />
          <Typography.Text type="secondary">
            {'(公斤/件/个)'}
          </Typography.Text>
          <Checkbox
            disabled={disabled}
            checked={ladderEnabled}
            onChange={(event) => {
              if (event.target.checked) {
                onWeightRangeChange?.({
                  base_qt: weightRange?.base_qt ?? 0,
                  step_qt: weightRange?.step_qt ?? 0,
                  step_weight: weightRange?.step_weight ?? null,
                });
              } else {
                onWeightRangeChange?.(null);
              }
            }}
          >
            {'产品计重阶梯设定'}
          </Checkbox>
        </Space>
      </div>

      {ladderEnabled ? (
        <div style={{ marginBottom: 16, paddingLeft: 118 }}>
          <div style={{ marginBottom: 10 }}>
            <Space wrap size={6} align="center">
              <span>
                {'买家购买'}
              </span>
              <InputNumber
                min={0}
                precision={0}
                disabled={disabled}
                value={toNumber(weightRange?.base_qt) ?? undefined}
                style={{ width: 88 }}
                onChange={(value) =>
                  patchRange({
                    base_qt: typeof value === 'number' ? value : null,
                  })
                }
              />
              <span>
                {'件/个以内，按单位产品重量计算运费。'}
              </span>
            </Space>
          </div>
          <div>
            <Space wrap size={6} align="center">
              <span>
                {'在此基础上，买家每多买'}
              </span>
              <InputNumber
                min={0}
                precision={0}
                disabled={disabled}
                value={toNumber(weightRange?.step_qt) ?? undefined}
                style={{ width: 88 }}
                onChange={(value) =>
                  patchRange({
                    step_qt: typeof value === 'number' ? value : null,
                  })
                }
              />
              <span>
                {'件/个，重量增加'}
              </span>
              <InputNumber
                min={0}
                step={0.01}
                disabled={disabled}
                value={toNumber(weightRange?.step_weight) ?? undefined}
                style={{ width: 88 }}
                onChange={(value) =>
                  patchRange({
                    step_weight: typeof value === 'number' ? value : null,
                  })
                }
              />
              <span>
                {'公斤。'}
              </span>
            </Space>
          </div>
        </div>
      ) : null}

      <div style={{ display: 'flex', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={labelStyle}>
          <Typography.Text type="danger">*</Typography.Text>
          {'包装后尺寸'}
          :
        </div>
        <Space wrap size={6} align="center" style={{ flex: 1, minWidth: 0 }}>
          <InputNumber
            min={0}
            step={0.1}
            disabled={disabled}
            value={toNumber(length) ?? undefined}
            style={{ width: 88 }}
            onChange={(value) =>
              onLengthChange?.(typeof value === 'number' ? value : null)
            }
          />
          <span>X</span>
          <InputNumber
            min={0}
            step={0.1}
            disabled={disabled}
            value={toNumber(width) ?? undefined}
            style={{ width: 88 }}
            onChange={(value) =>
              onWidthChange?.(typeof value === 'number' ? value : null)
            }
          />
          <span>X</span>
          <InputNumber
            min={0}
            step={0.1}
            disabled={disabled}
            value={toNumber(height) ?? undefined}
            style={{ width: 88 }}
            onChange={(value) =>
              onHeightChange?.(typeof value === 'number' ? value : null)
            }
          />
          <Typography.Text type="secondary">
            {'(单位: 厘米, 每件/个'}{' '}
            <Typography.Text type="danger">
              {volume == null ? '-' : volume}
            </Typography.Text>{' '}
            cm³)
          </Typography.Text>
        </Space>
      </div>
    </div>
  );
};

export default PackageInfoFields;
