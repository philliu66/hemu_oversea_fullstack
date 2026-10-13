import { ProFormDependency } from '@ant-design/pro-components';
import { Form, InputNumber, Radio, Select, Space, Typography } from 'antd';
import React, { useMemo } from 'react';
import type { DhItemInventoryPublic, DhMeasuresUnitPublic } from '@/types/api';
import { useMeasureUnits } from './measureUnits';

/** issample：2 成人 / 3 非成人（平台也可能返回其它值） */
export const ISSAMPLE_ADULT = '2';
export const ISSAMPLE_NON_ADULT = '3';

export type StockStatus = 'in_stock' | 'in_transit' | 'pending';

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

type SaleInfoFieldsProps = {
  disabled?: boolean;
};

/**
 * 销售信息：字段直连 Form；计件单位在本组件内加载（进程缓存）；
 * 销售方式/文案通过 ProFormDependency 订阅 measure_id / packing_quantity。
 */
const SaleInfoFields: React.FC<SaleInfoFieldsProps> = ({
  disabled = false,
}) => {
  const form = Form.useFormInstance();
  const measureId = Form.useWatch('measure_id', form) as
    | string
    | null
    | undefined;
  const { options: measureOptions, loading: measureOptionsLoading } =
    useMeasureUnits();
  const measureSelectOptions = useMemo(() => {
    const list = measureOptions.map((item) => ({
      label: formatMeasureLabel(item),
      value: item.measure_id,
    }));
    const current = (measureId || '').trim();
    if (!current || list.some((item) => item.value === current)) {
      return list;
    }
    return [{ label: current, value: current }, ...list];
  }, [measureId, measureOptions]);
  // options 从空到有时强制重建，避免回填的 measure_id 一直显示成裸 id
  const measureSelectKey = measureOptionsLoading
    ? 'measure-pending'
    : 'measure-ready';

  return (
    <>
      {/* packing_quantity / item_inventory 由 setFieldsValue 维护，无独立控件 */}
      <Form.Item name="measure_id" label={requiredLabel('计件单位')}>
        <Select
          key={measureSelectKey}
          disabled={disabled}
          loading={measureOptionsLoading}
          showSearch
          allowClear
          placeholder={'请选择计件单位'}
          options={measureSelectOptions}
          optionFilterProp="label"
          style={{ maxWidth: 280, width: '100%' }}
        />
      </Form.Item>

      <ProFormDependency
        name={['measure_id', 'packing_quantity', 'item_inventory']}
      >
        {({ measure_id, packing_quantity, item_inventory }) => {
          const packQty = packing_quantity == null ? 1 : packing_quantity;
          const sellByPack = packQty > 1;
          const measureUnitLabel =
            resolveMeasureDisplayName(measure_id, measureOptions) || '件';
          const stockStatus = deriveStockStatus(item_inventory);
          return (
            <>
              <Form.Item label={requiredLabel('销售方式')}>
                <Radio.Group
                  disabled={disabled}
                  value={sellByPack ? 'pack' : 'piece'}
                  onChange={(event) => {
                    if (event.target.value === 'piece') {
                      form.setFieldsValue({ packing_quantity: 1 });
                      return;
                    }
                    form.setFieldsValue({
                      packing_quantity: Math.max(packQty, 2),
                    });
                  }}
                >
                  <Radio value="piece">
                    {`按件卖 (单位: ${measureUnitLabel})`}
                  </Radio>
                  <Radio value="pack">
                    <Space size={6} align="center" wrap>
                      <span>{'按包卖 (每包产品的数量'}</span>
                      <InputNumber
                        min={2}
                        precision={0}
                        disabled={disabled || !sellByPack}
                        value={sellByPack ? packQty : undefined}
                        style={{ width: 88 }}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(value) => {
                          if (typeof value === 'number') {
                            form.setFieldsValue({ packing_quantity: value });
                          }
                        }}
                      />
                      <span>{measureUnitLabel})</span>
                    </Space>
                  </Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item label={requiredLabel('起定量')}>
                <Space size={8} align="center" wrap>
                  <Form.Item name="min_wholesale_qty" noStyle>
                    <InputNumber
                      min={1}
                      precision={0}
                      disabled={disabled}
                      style={{ width: 120 }}
                    />
                  </Form.Item>
                  <span>{sellByPack ? '包' : measureUnitLabel}</span>
                </Space>
              </Form.Item>

              <Form.Item label={requiredLabel('备货状态')}>
                <div>
                  <Radio.Group
                    disabled={disabled}
                    value={stockStatus}
                    onChange={(event) =>
                      form.setFieldsValue({
                        item_inventory: applyStockStatus(
                          item_inventory,
                          event.target.value,
                        ),
                      })
                    }
                  >
                    <Radio value="in_stock">{'有备货'}</Radio>
                    <Radio value="in_transit">{'备货途中'}</Radio>
                    <Radio value="pending">{'待备货'}</Radio>
                  </Radio.Group>
                  <div style={{ marginTop: 10 }}>
                    <Space size={8} align="center" wrap>
                      <span>{'一次最大购买数量为'}</span>
                      <Form.Item name="max_sale_qty" noStyle>
                        <InputNumber
                          min={1}
                          precision={0}
                          disabled={disabled}
                          style={{ width: 120 }}
                        />
                      </Form.Item>
                      <span>{sellByPack ? '包' : measureUnitLabel}</span>
                    </Space>
                  </div>
                </div>
              </Form.Item>
            </>
          );
        }}
      </ProFormDependency>

      <Form.Item label={requiredLabel('备货期')}>
        <Space size={8} align="center" wrap>
          <Form.Item name="leading_time" noStyle>
            <InputNumber
              min={0}
              precision={0}
              disabled={disabled}
              style={{ width: 120 }}
            />
          </Form.Item>
          <span>{'天'}</span>
        </Space>
      </Form.Item>
    </>
  );
};

export default SaleInfoFields;
