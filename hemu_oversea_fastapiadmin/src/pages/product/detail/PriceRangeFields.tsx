import { Button, InputNumber, Radio, Space, Typography } from 'antd';
import React, { useMemo } from 'react';
import type { DhItemWholesaleRangePublic } from '@/types/api';

/** priceConfigType：1 分别设置 / 2 统一设置 */
export const PRICE_CONFIG_SEPARATE = '1';
export const PRICE_CONFIG_UNIFIED = '2';

const MAX_RANGE_COUNT = 4;

type PriceRangeFieldsProps = {
  priceConfigType?: string | null;
  minWholesaleQty?: number | null;
  ranges?: DhItemWholesaleRangePublic[];
  /** 计件单位展示名，联动「购买 xx {unit}及以上」 */
  measureUnitLabel?: string;
  disabled?: boolean;
  onPriceConfigTypeChange?: (value: string) => void;
  onMinWholesaleQtyChange?: (value: number | null) => void;
  onRangesChange?: (next: DhItemWholesaleRangePublic[]) => void;
};

function toNumber(value: string | number | null | undefined): number | null {
  if (value == null || value === '') {
    return null;
  }
  const num = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(num) ? num : null;
}

/** 接口 discount 为小数（如 0.02）；UI 千分比展示为 2‰ */
function discountToPermille(
  value: string | number | null | undefined,
): number | null {
  const num = toNumber(value);
  if (num == null) {
    return null;
  }
  return Math.round(num * 100 * 1e6) / 1e6;
}

function permilleToDiscount(value: number | null): number | null {
  if (value == null) {
    return null;
  }
  return Math.round(value * 1e4) / 1e6;
}

/**
 * 价格区间：对应详情
 * - price_config_type ← itemSaleSetting.priceConfigType
 * - min_wholesale_qty ← itemSaleSetting.minWholesaleQty（首档）
 * - item_wholesale_range_list ← itemWholesaleRangeList（折扣档 startQty/discount，单位‰）
 */
const PriceRangeFields: React.FC<PriceRangeFieldsProps> = ({
  priceConfigType,
  minWholesaleQty,
  ranges,
  measureUnitLabel,
  disabled = false,
  onPriceConfigTypeChange,
  onMinWholesaleQtyChange,
  onRangesChange,
}) => {
  const list = useMemo(() => ranges || [], [ranges]);
  /** 首档 + 折扣档，合计最多 4 个 */
  const canAdd = 1 + list.length < MAX_RANGE_COUNT;
  const configType = priceConfigType || PRICE_CONFIG_SEPARATE;
  const unitLabel =
    (measureUnitLabel || '').trim() ||
    '件';

  const patchRange = (
    index: number,
    patch: Partial<DhItemWholesaleRangePublic>,
  ) => {
    if (disabled) {
      return;
    }
    const next = list.map((item, i) =>
      i === index ? { ...item, ...patch } : item,
    );
    onRangesChange?.(next);
  };

  const handleAdd = () => {
    if (disabled || !canAdd) {
      return;
    }
    const lastQty =
      list.length > 0
        ? toNumber(list[list.length - 1]?.start_qty)
        : toNumber(minWholesaleQty) ?? 1;
    onRangesChange?.([
      ...list,
      {
        start_qty: (lastQty || 1) + 1,
        discount: 0.01,
      },
    ]);
  };

  const handleRemove = (index: number) => {
    if (disabled) {
      return;
    }
    onRangesChange?.(list.filter((_, i) => i !== index));
  };

  return (
    <div style={{ marginTop: 24 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          columnGap: 12,
          marginBottom: 12,
        }}
      >
        <div
          style={{
            width: 88,
            flexShrink: 0,
            lineHeight: '32px',
            color: 'rgba(0,0,0,0.88)',
          }}
        >
          <Typography.Text type="danger">*</Typography.Text>
          {'价格区间'}
          :
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Typography.Text type="secondary" style={{ lineHeight: '32px' }}>
            {'您可以最多添加4个价格区间'}
          </Typography.Text>

          <div style={{ marginTop: 8, marginBottom: 12 }}>
            <Radio.Group
              disabled={disabled}
              value={configType}
              onChange={(event) =>
                onPriceConfigTypeChange?.(event.target.value)
              }
            >
              <Radio value={PRICE_CONFIG_UNIFIED}>
                {'统一设置价格'}
              </Radio>
              <Radio value={PRICE_CONFIG_SEPARATE}>
                {'分别设置价格'}
              </Radio>
            </Radio.Group>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <Space wrap size={6} align="center">
              <span>购买</span>
              <InputNumber
                min={1}
                precision={0}
                disabled={disabled}
                value={minWholesaleQty ?? undefined}
                style={{ width: 88 }}
                onChange={(value) =>
                  onMinWholesaleQtyChange?.(
                    typeof value === 'number' ? value : null,
                  )
                }
              />
              <span>{`${unitLabel}及以上时，为表格中填写的预计收入。`}</span>
            </Space>

            {list.map((item, index) => (
              <Space key={`range-${index}`} wrap size={6} align="center">
                <span>购买</span>
                <InputNumber
                  min={1}
                  precision={0}
                  disabled={disabled}
                  value={toNumber(item.start_qty) ?? undefined}
                  style={{ width: 88 }}
                  onChange={(value) =>
                    patchRange(index, {
                      start_qty: typeof value === 'number' ? value : null,
                    })
                  }
                />
                <span>{`${unitLabel}及以上时，预计收入降低`}</span>
                <InputNumber
                  min={0}
                  precision={0}
                  disabled={disabled}
                  value={discountToPermille(item.discount) ?? undefined}
                  style={{ width: 88 }}
                  onChange={(value) =>
                    patchRange(index, {
                      discount: permilleToDiscount(
                        typeof value === 'number' ? value : null,
                      ),
                    })
                  }
                />
                <span>‰</span>
                {!disabled ? (
                  <Button
                    type="link"
                    size="small"
                    style={{ paddingInline: 4 }}
                    onClick={() => handleRemove(index)}
                  >
                    删除
                  </Button>
                ) : null}
              </Space>
            ))}
          </div>

          {!disabled && canAdd ? (
            <div style={{ marginTop: 12 }}>
              <Button type="dashed" onClick={handleAdd}>
                {'添加价格区间'}
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default PriceRangeFields;
