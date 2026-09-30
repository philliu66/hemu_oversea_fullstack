import { useIntl } from '@umijs/max';
import { Form, InputNumber, Radio, Select, Space, Typography } from 'antd';
import React, { useMemo } from 'react';
import type {
  DhItemInventoryPublic,
  DhMeasuresUnitPublic,
} from '@/types/api';

/** issample：2 成人 / 3 非成人（平台也可能返回其它值） */
export const ISSAMPLE_ADULT = '2';
export const ISSAMPLE_NON_ADULT = '3';

export type StockStatus = 'in_stock' | 'in_transit' | 'pending';

type SaleInfoFieldsProps = {
  measureId?: string | null;
  measureOptions?: DhMeasuresUnitPublic[];
  measuresLoading?: boolean;
  packingQuantity?: number | null;
  minWholesaleQty?: number | null;
  itemInventory?: DhItemInventoryPublic | null;
  maxSaleQty?: number | null;
  leadingTime?: number | null;
  disabled?: boolean;
  onMeasureIdChange?: (value: string | null) => void;
  onPackingQuantityChange?: (value: number | null) => void;
  onMinWholesaleQtyChange?: (value: number | null) => void;
  onItemInventoryChange?: (value: DhItemInventoryPublic | null) => void;
  onMaxSaleQtyChange?: (value: number | null) => void;
  onLeadingTimeChange?: (value: number | null) => void;
};

export function formatMeasureLabel(item: DhMeasuresUnitPublic): string {
  const cn = (item.cname || '').trim();
  const en = (item.name || '').trim();
  if (cn && en && cn !== en) {
    return `${cn}(${en})`;
  }
  return cn || en || item.short_name || item.measure_id;
}

export function resolveMeasureDisplayName(
  measureId: string | null | undefined,
  options?: DhMeasuresUnitPublic[],
): string | undefined {
  const id = (measureId || '').trim();
  if (!id) {
    return undefined;
  }
  const hit = (options || []).find((item) => item.measure_id === id);
  if (hit) {
    return (hit.cname || hit.name || hit.short_name || id).trim() || id;
  }
  return id;
}

function isInTransit(inv?: DhItemInventoryPublic | null): boolean {
  return (inv?.inventory_location_list || []).some(
    (item) => String(item.if_in_transit) === '1',
  );
}

export function deriveStockStatus(
  inv?: DhItemInventoryPublic | null,
): StockStatus {
  if (!inv) {
    return 'pending';
  }
  if (isInTransit(inv)) {
    return 'in_transit';
  }
  if (String(inv.inventory_status) === '1') {
    return 'in_stock';
  }
  return 'pending';
}

function applyStockStatus(
  prev: DhItemInventoryPublic | null | undefined,
  status: StockStatus,
): DhItemInventoryPublic {
  const base: DhItemInventoryPublic = {
    inventory_location: prev?.inventory_location ?? null,
    subtract_stock_type: prev?.subtract_stock_type ?? null,
    inventory_ori_qty: prev?.inventory_ori_qty ?? null,
    inventory_qty: prev?.inventory_qty ?? null,
    inventory_location_list: prev?.inventory_location_list
      ? [...prev.inventory_location_list]
      : [],
  };
  if (status === 'in_stock') {
    return {
      ...base,
      inventory_status: '1',
      inventory_location_list: (base.inventory_location_list || []).map(
        (item) => ({ ...item, if_in_transit: '0' }),
      ),
    };
  }
  if (status === 'in_transit') {
    const list = [...(base.inventory_location_list || [])];
    if (list.length === 0) {
      list.push({
        inventory_location: base.inventory_location,
        if_in_transit: '1',
      });
    } else {
      list[0] = { ...list[0], if_in_transit: '1' };
    }
    return {
      ...base,
      inventory_status: '1',
      inventory_location_list: list,
    };
  }
  return {
    ...base,
    inventory_status: '0',
    inventory_location_list: (base.inventory_location_list || []).map(
      (item) => ({ ...item, if_in_transit: '0' }),
    ),
  };
}

function requiredLabel(text: string) {
  return (
    <span>
      <Typography.Text type="danger">*</Typography.Text>
      {text}
    </span>
  );
}

/**
 * 销售信息卡片字段：计件单位、销售方式、起定量、备货状态、备货期。
 * 与产品分组等同级 Form.Item，标签对齐表单 labelCol。
 */
const SaleInfoFields: React.FC<SaleInfoFieldsProps> = ({
  measureId,
  measureOptions,
  measuresLoading = false,
  packingQuantity,
  minWholesaleQty,
  itemInventory,
  maxSaleQty,
  leadingTime,
  disabled = false,
  onMeasureIdChange,
  onPackingQuantityChange,
  onMinWholesaleQtyChange,
  onItemInventoryChange,
  onMaxSaleQtyChange,
  onLeadingTimeChange,
}) => {
  const intl = useIntl();
  const stockStatus = deriveStockStatus(itemInventory);
  const packQty = packingQuantity == null ? 1 : packingQuantity;
  const sellByPack = packQty > 1;
  const measureUnitLabel =
    resolveMeasureDisplayName(measureId, measureOptions) ||
    intl.formatMessage({
      id: 'pages.product.detail.sale.measureFallback',
      defaultMessage: '件',
    });

  const selectOptions = useMemo(() => {
    const list = measureOptions || [];
    const options = list.map((item) => ({
      label: formatMeasureLabel(item),
      value: item.measure_id,
    }));
    const current = (measureId || '').trim();
    if (current && !options.some((item) => item.value === current)) {
      options.unshift({ label: current, value: current });
    }
    return options;
  }, [measureId, measureOptions]);

  return (
    <>
      <Form.Item
        label={requiredLabel(
          intl.formatMessage({
            id: 'pages.product.detail.sale.measure',
            defaultMessage: '计件单位',
          }),
        )}
      >
        <Select
          disabled={disabled}
          allowClear
          showSearch
          loading={measuresLoading}
          optionFilterProp="label"
          style={{ maxWidth: 280, width: '100%' }}
          placeholder={intl.formatMessage({
            id: 'pages.product.detail.sale.measurePlaceholder',
            defaultMessage: '请选择计件单位',
          })}
          options={selectOptions}
          value={measureId || undefined}
          onChange={(value) => onMeasureIdChange?.(value || null)}
        />
      </Form.Item>

      <Form.Item
        label={requiredLabel(
          intl.formatMessage({
            id: 'pages.product.detail.sale.saleMethod',
            defaultMessage: '销售方式',
          }),
        )}
      >
        <Radio.Group
          disabled={disabled}
          value={sellByPack ? 'pack' : 'piece'}
          onChange={(event) => {
            if (event.target.value === 'piece') {
              onPackingQuantityChange?.(1);
              return;
            }
            onPackingQuantityChange?.(Math.max(packQty, 2));
          }}
        >
          <Radio value="piece">
            {intl.formatMessage(
              {
                id: 'pages.product.detail.sale.sellByPieceWithUnit',
                defaultMessage: '按件卖 (单位: {unit})',
              },
              { unit: measureUnitLabel },
            )}
          </Radio>
          <Radio value="pack">
            <Space size={6} align="center" wrap>
              <span>
                {intl.formatMessage({
                  id: 'pages.product.detail.sale.sellByPack',
                  defaultMessage: '按包卖 (每包产品的数量',
                })}
              </span>
              <InputNumber
                min={2}
                precision={0}
                disabled={disabled || !sellByPack}
                value={sellByPack ? packQty : undefined}
                style={{ width: 88 }}
                onClick={(event) => event.stopPropagation()}
                onChange={(value) => {
                  if (typeof value === 'number') {
                    onPackingQuantityChange?.(value);
                  }
                }}
              />
              <span>{measureUnitLabel})</span>
            </Space>
          </Radio>
        </Radio.Group>
      </Form.Item>

      <Form.Item
        label={requiredLabel(
          intl.formatMessage({
            id: 'pages.product.detail.sale.minWholesaleQty',
            defaultMessage: '起定量',
          }),
        )}
      >
        <Space size={8} align="center" wrap>
          <InputNumber
            min={1}
            precision={0}
            disabled={disabled}
            value={minWholesaleQty ?? undefined}
            style={{ width: 120 }}
            onChange={(value) =>
              onMinWholesaleQtyChange?.(
                typeof value === 'number' ? value : null,
              )
            }
          />
          <span>
            {sellByPack
              ? intl.formatMessage({
                  id: 'pages.product.detail.sale.minWholesaleQtyPack',
                  defaultMessage: '包',
                })
              : measureUnitLabel}
          </span>
        </Space>
      </Form.Item>

      <Form.Item
        label={requiredLabel(
          intl.formatMessage({
            id: 'pages.product.detail.sale.stockStatus',
            defaultMessage: '备货状态',
          }),
        )}
      >
        <div>
          <Radio.Group
            disabled={disabled}
            value={stockStatus}
            onChange={(event) =>
              onItemInventoryChange?.(
                applyStockStatus(itemInventory, event.target.value),
              )
            }
          >
            <Radio value="in_stock">
              {intl.formatMessage({
                id: 'pages.product.detail.sale.stockInStock',
                defaultMessage: '有备货',
              })}
            </Radio>
            <Radio value="in_transit">
              {intl.formatMessage({
                id: 'pages.product.detail.sale.stockInTransit',
                defaultMessage: '备货途中',
              })}
            </Radio>
            <Radio value="pending">
              {intl.formatMessage({
                id: 'pages.product.detail.sale.stockPending',
                defaultMessage: '待备货',
              })}
            </Radio>
          </Radio.Group>
          <div style={{ marginTop: 10 }}>
            <Space size={8} align="center" wrap>
              <span>
                {intl.formatMessage({
                  id: 'pages.product.detail.sale.maxSaleQtyPrefix',
                  defaultMessage: '一次最大购买数量为',
                })}
              </span>
              <InputNumber
                min={1}
                precision={0}
                disabled={disabled}
                value={maxSaleQty ?? undefined}
                style={{ width: 120 }}
                onChange={(value) =>
                  onMaxSaleQtyChange?.(
                    typeof value === 'number' ? value : null,
                  )
                }
              />
              <span>
                {sellByPack
                  ? intl.formatMessage({
                      id: 'pages.product.detail.sale.maxSaleQtyPack',
                      defaultMessage: '包',
                    })
                  : measureUnitLabel}
              </span>
            </Space>
          </div>
        </div>
      </Form.Item>

      <Form.Item
        label={requiredLabel(
          intl.formatMessage({
            id: 'pages.product.detail.sale.leadingTime',
            defaultMessage: '备货期',
          }),
        )}
      >
        <Space size={8} align="center" wrap>
          <InputNumber
            min={0}
            precision={0}
            disabled={disabled}
            value={leadingTime ?? undefined}
            style={{ width: 120 }}
            onChange={(value) =>
              onLeadingTimeChange?.(typeof value === 'number' ? value : null)
            }
          />
          <span>
            {intl.formatMessage({
              id: 'pages.product.detail.sale.leadingTimeUnit',
              defaultMessage: '天',
            })}
          </span>
        </Space>
      </Form.Item>
    </>
  );
};

export default SaleInfoFields;
