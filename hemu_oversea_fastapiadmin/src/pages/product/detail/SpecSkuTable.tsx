import { InfoCircleOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { useModel, useSearchParams } from '@umijs/max';
import {
  App,
  Button,
  Input,
  InputNumber,
  Modal,
  Popover,
  Select,
  Space,
  Spin,
  Typography,
} from 'antd';
import React, { useMemo, useState } from 'react';
import { fetchDhSkuBaseInfo } from '@/services/common/utils';
import type {
  DhCommissionUnitPublic,
  DhProductSelectedAttrPublic,
  DhProductSkuPublic,
  DhProductSpecSelfDefPublic,
  DhSkuBaseInfoPublic,
  StoreBaseDiscountPublic,
} from '@/types/api';
import { resolveRequestSupplierId } from '@/utils/portalScope';
import { collectDistinctSkuSpecModels } from './CommissionRateHint';
import { applyAutoSkuRetailPrices } from './skuAutoPrice';

function useScopedSupplierId(propSupplierId?: number | null): number | undefined {
  const { initialState } = useModel('@@initialState');
  const [searchParams] = useSearchParams();
  const queryRaw = Number(searchParams.get('supplier_id'));
  const fromQuery =
    Number.isInteger(queryRaw) && queryRaw > 0 ? queryRaw : undefined;
  const fromProp =
    typeof propSupplierId === 'number' && propSupplierId > 0
      ? propSupplierId
      : undefined;
  return resolveRequestSupplierId(
    initialState?.currentUser,
    fromProp ?? fromQuery,
  );
}

const CUSTOM_SPEC_COL = '__custom_spec__';

type SpecSkuTableProps = {
  skuList?: DhProductSkuPublic[];
  priceSelectedAttrs?: DhProductSelectedAttrPublic[];
  specSelfDefs?: DhProductSpecSelfDefPublic[];
  itemCode?: string | null;
  /** 价格列单位后缀，联动计件单位（如 套） */
  measureUnitLabel?: string;
  supplierId?: number | null;
  storeId?: number | null;
  commissionUnits?: DhCommissionUnitPublic[];
  storeDiscount?: StoreBaseDiscountPublic | null;
  disabled?: boolean;
  onChange?: (next: DhProductSkuPublic[]) => void;
};

type AttrColumnDef = {
  key: string;
  title: string;
};

type BatchField = 'sale_status' | 'retail_price';

function attrColumnTitle(attr: DhProductSelectedAttrPublic): string {
  return attr.attr_name_cn?.trim() || attr.attr_name?.trim() || attr.attr_id;
}

function valueLabelFromAttr(
  attr: DhProductSelectedAttrPublic | undefined,
  attrValId: string | null | undefined,
): string {
  if (!attr || !attrValId) {
    return '';
  }
  const found = (attr.values || []).find(
    (item) => String(item.attr_val_id) === String(attrValId),
  );
  if (!found) {
    return '';
  }
  const en = found.line_attrval_name?.trim() || '';
  const cn = found.line_attrval_name_cn?.trim() || '';
  if (cn) {
    return cn;
  }
  return en || attrValId;
}

function buildAttrValueMap(
  sku: DhProductSkuPublic,
  priceAttrs: DhProductSelectedAttrPublic[],
  specs: DhProductSpecSelfDefPublic[],
): Record<string, string> {
  const priceById = new Map(
    priceAttrs.map((item) => [String(item.attr_id), item]),
  );
  const specByValId = new Map(
    specs
      .filter((item) => item.attr_val_id)
      .map((item) => [String(item.attr_val_id), item.attr_val_name || '']),
  );
  const result: Record<string, string> = {};
  const attrs = sku.item_sku_attr_value_list || [];

  for (const item of attrs) {
    const attrId = item.attr_id ? String(item.attr_id) : '';
    const valId = item.attr_val_id ? String(item.attr_val_id) : '';
    if (item.size_spec_type === '3' || (valId && specByValId.has(valId))) {
      result[CUSTOM_SPEC_COL] =
        specByValId.get(valId) || result[CUSTOM_SPEC_COL] || valId;
      continue;
    }
    if (!attrId) {
      continue;
    }
    const label = valueLabelFromAttr(priceById.get(attrId), valId);
    result[attrId] = label || valId;
  }

  if (Object.keys(result).length === 0 && sku.attr_combo_text) {
    const parts = sku.attr_combo_text
      .split(/\s*[/|｜]\s*/)
      .map((item) => item.trim())
      .filter(Boolean);
    priceAttrs.forEach((attr, index) => {
      if (parts[index]) {
        result[String(attr.attr_id)] = parts[index];
      }
    });
    if (specs.length && parts.length > priceAttrs.length) {
      result[CUSTOM_SPEC_COL] = parts.slice(priceAttrs.length).join(' / ');
    } else if (!priceAttrs.length && parts.length) {
      result[CUSTOM_SPEC_COL] = parts.join(' / ');
    }
  }

  return result;
}

function skuRowKey(record: DhProductSkuPublic): string {
  return String(
    record.id || record.sku_id || record.sku_md5 || record.sku_code || '',
  );
}

function formatUsdPrice(value: string | number | null | undefined): string {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return '-';
  }
  return `$${num.toFixed(2)}`;
}

function toFiniteNumber(value: string | number | null | undefined): number | null {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

/** 0.08 或 8 → 0.08 */
function rateToDecimal(value: string | number | null | undefined): number | null {
  const text = String(value ?? '').trim().replace(/%$/, '');
  if (!text) {
    return null;
  }
  const num = Number(text);
  if (!Number.isFinite(num)) {
    return null;
  }
  if (Math.abs(num) <= 1) {
    return num;
  }
  return num / 100;
}

function formatPercent(value: string | number | null | undefined): string {
  const decimal = rateToDecimal(value);
  if (decimal == null) {
    return '-';
  }
  const pct = decimal * 100;
  const fixed = Number.isInteger(pct)
    ? String(pct)
    : pct.toFixed(2).replace(/\.?0+$/, '');
  return `${fixed}%`;
}

function formatBound(value: string | null | undefined): string {
  const text = (value || '').trim();
  if (!text) {
    return '∞';
  }
  return text;
}

function formatAmountRange(unit: DhCommissionUnitPublic): string {
  const leftBracket = unit.left_bound_close === false ? '(' : '[';
  const rightBracket = unit.right_bound_close === false ? ')' : ']';
  return `${leftBracket}${formatBound(unit.left_bound)}, ${formatBound(
    unit.right_bound,
  )}${rightBracket}`;
}

function amountInUnit(
  amount: number,
  unit: DhCommissionUnitPublic,
): boolean {
  const leftText = (unit.left_bound || '').trim();
  const rightText = (unit.right_bound || '').trim();
  const left = leftText ? Number(leftText) : Number.NEGATIVE_INFINITY;
  const right = rightText ? Number(rightText) : Number.POSITIVE_INFINITY;
  const leftOk = Number.isFinite(left)
    ? unit.left_bound_close === false
      ? amount > left
      : amount >= left
    : true;
  const rightOk = Number.isFinite(right)
    ? unit.right_bound_close === false
      ? amount < right
      : amount <= right
    : true;
  return leftOk && rightOk;
}

function matchCommissionUnit(
  amount: number,
  units: DhCommissionUnitPublic[],
): DhCommissionUnitPublic | null {
  const sorted = [...units].sort((a, b) => {
    const leftA = Number(a.left_bound);
    const leftB = Number(b.left_bound);
    if (Number.isFinite(leftA) && Number.isFinite(leftB)) {
      return leftA - leftB;
    }
    return String(a.left_bound || '').localeCompare(String(b.left_bound || ''));
  });
  return sorted.find((unit) => amountInUnit(amount, unit)) || null;
}

function SkuRetailPriceHint({
  skuCode,
  supplierId,
  commissionUnits,
  storeDiscount,
}: {
  skuCode?: string | null;
  supplierId?: number | null;
  commissionUnits?: DhCommissionUnitPublic[];
  storeDiscount?: StoreBaseDiscountPublic | null;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState<DhSkuBaseInfoPublic | null>(null);
  const [error, setError] = useState<string | null>(null);

  const skuText = String(skuCode ?? '').trim();
  const canQuery =
    typeof supplierId === 'number' && supplierId > 0 && Boolean(skuText);

  const loadInfo = async () => {
    if (!canQuery) {
      setInfo(null);
      setError(
        typeof supplierId === 'number' && supplierId > 0
          ? '当前 SKU 编码为空'
          : '未指定供应商，无法查询基础信息',
      );
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // 原样上送 sku_code，清洗由后端统一处理
      const data = await fetchDhSkuBaseInfo(
        { supplier_id: supplierId, sku_code: skuText },
        { skipErrorHandler: true },
      );
      setInfo(data);
    } catch {
      setInfo(null);
      setError('暂无该 SKU 型号的基础信息');
    } finally {
      setLoading(false);
    }
  };

  const unitPrice = toFiniteNumber(info?.unit_price);
  const packingQty =
    typeof info?.packing_quantity === 'number' && info.packing_quantity > 0
      ? info.packing_quantity
      : null;
  const moq =
    typeof info?.min_wholesale_qty === 'number' && info.min_wholesale_qty > 0
      ? info.min_wholesale_qty
      : null;
  const salesUnit =
    packingQty != null && moq != null ? packingQty * moq : null;
  const orderAmount =
    unitPrice != null && salesUnit != null ? unitPrice * salesUnit : null;
  const matchedUnit =
    orderAmount != null
      ? matchCommissionUnit(orderAmount, commissionUnits || [])
      : null;
  const commissionDecimal = rateToDecimal(matchedUnit?.commission_rate);
  const discountDecimal = rateToDecimal(storeDiscount?.base_discount);
  const listPrice =
    unitPrice != null &&
    packingQty != null &&
    commissionDecimal != null &&
    discountDecimal != null &&
    discountDecimal > 0
      ? (unitPrice * packingQty * (1 - commissionDecimal)) / discountDecimal
      : null;

  const content = (
    <div style={{ minWidth: 240, maxWidth: 360 }}>
      {loading ? (
        <Spin size="small" />
      ) : error ? (
        <Typography.Text type="secondary">{error}</Typography.Text>
      ) : info ? (
        <Space direction="vertical" size={2}>
          <Typography.Text>
            {'SKU 编码 '}
            <Typography.Text strong>{info.sku_code}</Typography.Text>
          </Typography.Text>
          <Typography.Text>
            {'基础价格 '}
            <Typography.Text strong>
              {formatUsdPrice(info.unit_price)}
            </Typography.Text>
          </Typography.Text>
          <Typography.Text>
            {'销售单元 '}
            <Typography.Text strong>
              {salesUnit == null ? '-' : String(salesUnit)}
            </Typography.Text>
            {packingQty != null && moq != null ? (
              <Typography.Text type="secondary" style={{ marginLeft: 4 }}>
                {`（打包数 ${packingQty} × 起订量 ${moq}）`}
              </Typography.Text>
            ) : null}
          </Typography.Text>
          <Typography.Text>
            {'类目佣金率 '}
            {orderAmount == null ? (
              <Typography.Text type="secondary">{'无法计算订单金额'}</Typography.Text>
            ) : matchedUnit && commissionDecimal != null ? (
              <>
                <Typography.Text strong>
                  {formatPercent(matchedUnit.commission_rate)}
                </Typography.Text>
                <Typography.Text type="secondary" style={{ display: 'block' }}>
                  {`订单金额 ${formatUsdPrice(orderAmount)}，区间 ${formatAmountRange(matchedUnit)}`}
                </Typography.Text>
              </>
            ) : (
              <Typography.Text type="secondary">
                {`订单金额 ${formatUsdPrice(orderAmount)}，未匹配到佣金区间`}
              </Typography.Text>
            )}
          </Typography.Text>
          <Typography.Text>
            {'店铺折扣 '}
            <Typography.Text strong>
              {storeDiscount ? formatPercent(storeDiscount.base_discount) : '-'}
            </Typography.Text>
          </Typography.Text>
          <Typography.Text>
            {'标价 '}
            <Typography.Text strong>
              {listPrice == null ? '-' : formatUsdPrice(listPrice)}
            </Typography.Text>
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {'标价 = 基础价格 × 打包数 ×（1 − 佣金率）/ 店铺折扣'}
          </Typography.Text>
          {unitPrice != null &&
          packingQty != null &&
          commissionDecimal != null &&
          discountDecimal != null ? (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {`= ${formatUsdPrice(unitPrice)} × ${packingQty} ×（1 − ${formatPercent(
                matchedUnit?.commission_rate,
              )}）/ ${formatPercent(storeDiscount?.base_discount)}`}
            </Typography.Text>
          ) : null}
        </Space>
      ) : (
        <Typography.Text type="secondary">{'点击图标查看基础信息'}</Typography.Text>
      )}
    </div>
  );

  return (
    <Popover
      trigger="click"
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) {
          void loadInfo();
        }
      }}
      content={content}
      title={'SKU 基础信息'}
    >
      <InfoCircleOutlined
        style={{ cursor: 'pointer', color: 'rgba(0,0,0,0.45)' }}
        onClick={(event) => {
          event.stopPropagation();
        }}
      />
    </Popover>
  );
}

const SpecSkuTable: React.FC<SpecSkuTableProps> = ({
  skuList,
  priceSelectedAttrs,
  specSelfDefs,
  itemCode,
  measureUnitLabel,
  supplierId: supplierIdProp,
  storeId,
  commissionUnits,
  storeDiscount,
  disabled = false,
  onChange,
}) => {
  const { message } = App.useApp();
  const supplierId = useScopedSupplierId(supplierIdProp);
  const list = skuList || [];
  const priceAttrs = priceSelectedAttrs || [];
  const specs = specSelfDefs || [];
  const unitLabel =
    (measureUnitLabel || '').trim() ||
    '件';
  const priceUnitSuffix = `/${unitLabel}`;

  const [batchField, setBatchField] = useState<BatchField>();
  const [batchDrafts, setBatchDrafts] = useState<DhProductSkuPublic[]>([]);
  const [batchUniform, setBatchUniform] = useState<string | number | null>();
  const [autoPriceLoading, setAutoPriceLoading] = useState(false);

  const attrColumns: AttrColumnDef[] = useMemo(() => {
    const cols: AttrColumnDef[] = priceAttrs.map((attr) => ({
      key: String(attr.attr_id),
      title: attrColumnTitle(attr),
    }));
    const hasCustom =
      specs.length > 0 ||
      list.some((sku) =>
        (sku.item_sku_attr_value_list || []).some(
          (item) =>
            item.size_spec_type === '3' ||
            (item.attr_val_id &&
              specs.some(
                (spec) =>
                  String(spec.attr_val_id) === String(item.attr_val_id),
              )),
        ),
      );
    if (hasCustom || cols.length === 0) {
      cols.push({
        key: CUSTOM_SPEC_COL,
        title: '自定义规格',
      });
    }
    return cols;
  }, [list, priceAttrs, specs]);

  const { sortedList, resolvedRows } = useMemo(() => {
    const withResolved = list.map((sku, index) => ({
      sku,
      index,
      values: buildAttrValueMap(sku, priceAttrs, specs),
    }));
    const keys = attrColumns.map((item) => item.key);
    withResolved.sort((a, b) => {
      for (const key of keys) {
        const left = a.values[key] || '';
        const right = b.values[key] || '';
        if (left !== right) {
          return left.localeCompare(right, 'zh-CN');
        }
      }
      return a.index - b.index;
    });
    return {
      sortedList: withResolved.map((item) => item.sku),
      resolvedRows: withResolved.map((item) => item.values),
    };
  }, [attrColumns, list, priceAttrs, specs]);

  const resolvedByKey = useMemo(() => {
    const map = new Map<string, Record<string, string>>();
    sortedList.forEach((sku, index) => {
      map.set(skuRowKey(sku), resolvedRows[index] || {});
    });
    return map;
  }, [resolvedRows, sortedList]);

  const patchSku = (index: number, patch: Partial<DhProductSkuPublic>) => {
    const target = sortedList[index];
    if (!target) {
      return;
    }
    const next = list.map((item) =>
      item === target ||
      (item.id && target.id && item.id === target.id) ||
      (item.sku_id && target.sku_id && item.sku_id === target.sku_id)
        ? { ...item, ...patch }
        : item,
    );
    onChange?.(next);
  };

  const openBatchModal = (field: BatchField) => {
    setBatchField(field);
    setBatchDrafts(sortedList.map((item) => ({ ...item })));
    setBatchUniform(undefined);
  };

  const closeBatchModal = () => {
    setBatchField(undefined);
    setBatchDrafts([]);
    setBatchUniform(undefined);
  };

  const patchBatchDraft = (
    index: number,
    patch: Partial<DhProductSkuPublic>,
  ) => {
    setBatchDrafts((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  };

  const applyUniformToDrafts = () => {
    if (batchField === 'sale_status') {
      const value =
        batchUniform === undefined || batchUniform === null
          ? null
          : String(batchUniform);
      setBatchDrafts((prev) =>
        prev.map((item) => ({ ...item, sale_status: value })),
      );
      return;
    }
    if (batchField === 'retail_price') {
      const value =
        batchUniform === undefined || batchUniform === null
          ? null
          : Number(batchUniform);
      setBatchDrafts((prev) =>
        prev.map((item) => ({
          ...item,
          retail_price: value == null || Number.isNaN(value) ? null : value,
        })),
      );
    }
  };

  const confirmBatchModal = () => {
    if (!batchField) {
      return;
    }
    const draftMap = new Map(
      batchDrafts.map((item) => [skuRowKey(item), item]),
    );
    const next = list.map((item) => {
      const draft = draftMap.get(skuRowKey(item));
      if (!draft) {
        return item;
      }
      if (batchField === 'sale_status') {
        return { ...item, sale_status: draft.sale_status };
      }
      return { ...item, retail_price: draft.retail_price };
    });
    onChange?.(next);
    closeBatchModal();
  };

  const generateSkuCodes = () => {
    const prefix = (itemCode || 'SKU').trim() || 'SKU';
    onChange?.(
      sortedList.map((item, index) => ({
        ...item,
        sku_code: `${prefix}-${String(index + 1).padStart(2, '0')}`,
      })),
    );
  };

  const autoSetRetailPrices = async () => {
    if (typeof supplierId !== 'number' || supplierId <= 0) {
      message.warning('未指定供应商，无法自动设置预计收入');
      return;
    }
    if (typeof storeId !== 'number' || storeId <= 0) {
      message.warning('请先选择店铺，再自动设置预计收入');
      return;
    }
    const models = collectDistinctSkuSpecModels(list);
    if (models.length === 0) {
      message.warning('暂无可识别的 SKU 型号，无法自动设置');
      return;
    }

    setAutoPriceLoading(true);
    try {
      const result = await applyAutoSkuRetailPrices(list, {
        supplierId,
        storeId,
      });
      if (result.updatedCount === 0) {
        message.error('未能获取任何 SKU 标价，请检查基础信息与佣金/折扣配置');
        return;
      }
      onChange?.(result.next);
      if (result.failedCount > 0) {
        message.warning(
          `已更新 ${result.updatedCount} 条预计收入；${result.failedCount} 个型号获取标价失败`,
        );
      } else {
        message.success(`已按标价自动设置 ${result.updatedCount} 条预计收入`);
      }
    } finally {
      setAutoPriceLoading(false);
    }
  };

  const saleOptions = [
    {
      value: '1',
      label: '可销售',
    },
    {
      value: '0',
      label: '不可销售',
    },
  ];

  const attrProColumns: ProColumns<DhProductSkuPublic>[] = attrColumns.map(
    (col) => ({
      title: col.title,
      key: col.key,
      width: 120,
      align: 'center',
      search: false,
      ellipsis: true,
      render: (_, record) =>
        resolvedByKey.get(skuRowKey(record))?.[col.key] || '-',
    }),
  );

  const columns: ProColumns<DhProductSkuPublic>[] = [
    ...attrProColumns,
    {
      title: (
        <Space size={4} wrap>
          <span>
            <span style={{ color: '#ff4d4f', marginRight: 2 }}>*</span>
            {'销售状态'}
          </span>
          {!disabled ? (
            <Button
              type="link"
              size="small"
              style={{ paddingInline: 4 }}
              onClick={() => openBatchModal('sale_status')}
            >
              {'批量设置'}
            </Button>
          ) : null}
        </Space>
      ),
      dataIndex: 'sale_status',
      width: 140,
      search: false,
      render: (_, record, index) => (
        <Select
          value={record.sale_status ?? undefined}
          style={{ width: '100%' }}
          options={saleOptions}
          disabled={disabled}
          onChange={(value) => patchSku(index, { sale_status: value })}
        />
      ),
    },
    {
      title: (
        <Space size={4} wrap>
          <span>
            <span style={{ color: '#ff4d4f', marginRight: 2 }}>*</span>
            {'预计收入'}
          </span>
          {!disabled ? (
            <>
              <Button
                type="link"
                size="small"
                style={{ paddingInline: 4 }}
                onClick={() => openBatchModal('retail_price')}
              >
                {'批量设置'}
              </Button>
              <Button
                type="link"
                size="small"
                style={{ paddingInline: 4 }}
                loading={autoPriceLoading}
                onClick={() => {
                  void autoSetRetailPrices();
                }}
              >
                {'自动设置'}
              </Button>
            </>
          ) : null}
        </Space>
      ),
      dataIndex: 'retail_price',
      width: 240,
      search: false,
      render: (_, record, index) => {
        const num =
          record.retail_price === null || record.retail_price === undefined
            ? undefined
            : Number(record.retail_price);
        return (
          <Space size={6} align="center">
            <InputNumber
              value={Number.isFinite(num) ? num : undefined}
              min={0}
              precision={2}
              disabled={disabled}
              addonBefore="US$"
              addonAfter={priceUnitSuffix}
              style={{ width: 180 }}
              onChange={(value) =>
                patchSku(index, {
                  retail_price: value == null ? null : value,
                })
              }
            />
            <SkuRetailPriceHint
              skuCode={record.sku_code}
              supplierId={supplierId}
              commissionUnits={commissionUnits}
              storeDiscount={storeDiscount}
            />
          </Space>
        );
      },
    },
    {
      title: (
        <Space size={4} wrap>
          <span>
            {'商品编码'}
          </span>
          {!disabled ? (
            <Button
              type="link"
              size="small"
              style={{ paddingInline: 4 }}
              onClick={generateSkuCodes}
            >
              {'一键生成'}
            </Button>
          ) : null}
        </Space>
      ),
      dataIndex: 'sku_code',
      width: 160,
      search: false,
      render: (_, record, index) => (
        <Input
          value={record.sku_code || ''}
          allowClear
          disabled={disabled}
          onChange={(event) =>
            patchSku(index, { sku_code: event.target.value || null })
          }
        />
      ),
    },
  ];

  const batchModalColumns: ProColumns<DhProductSkuPublic>[] = [
    ...attrProColumns,
    batchField === 'sale_status'
      ? {
          title: '销售状态',
          dataIndex: 'sale_status',
          width: 160,
          search: false,
          render: (_, record, index) => (
            <Select
              value={record.sale_status ?? undefined}
              style={{ width: '100%' }}
              options={saleOptions}
              onChange={(value) =>
                patchBatchDraft(index, { sale_status: value })
              }
            />
          ),
        }
      : {
          title: '预计收入',
          dataIndex: 'retail_price',
          width: 200,
          search: false,
          render: (_, record, index) => {
            const num =
              record.retail_price === null ||
              record.retail_price === undefined
                ? undefined
                : Number(record.retail_price);
            return (
              <InputNumber
                value={Number.isFinite(num) ? num : undefined}
                min={0}
                precision={2}
                addonBefore="US$"
                addonAfter={priceUnitSuffix}
                style={{ width: '100%' }}
                onChange={(value) =>
                  patchBatchDraft(index, {
                    retail_price: value == null ? null : value,
                  })
                }
              />
            );
          },
        },
  ];

  return (
    <>
      <ProTable<DhProductSkuPublic>
        rowKey={skuRowKey}
        search={false}
        options={false}
        toolBarRender={false}
        pagination={false}
        dataSource={sortedList}
        columns={columns}
        size="small"
        bordered
        scroll={{
          x: Math.max(860, attrColumns.length * 120 + 500),
        }}
        locale={{
          emptyText: '暂无根据规格生成的 SKU',
        }}
      />

      <Modal
        open={Boolean(batchField)}
        title={
          batchField === 'sale_status'
            ? '批量设置销售状态'
            : '批量设置预计收入'
        }
        width={880}
        destroyOnHidden
        onCancel={closeBatchModal}
        onOk={confirmBatchModal}
        okText={'确定'}
        cancelText={'取消'}
      >
        <Space style={{ marginBottom: 12 }} wrap>
          <Typography.Text>
            {'统一设置'}
            :
          </Typography.Text>
          {batchField === 'sale_status' ? (
            <Select
              allowClear
              placeholder={'销售状态'}
              style={{ width: 160 }}
              options={saleOptions}
              value={
                batchUniform === undefined || batchUniform === null
                  ? undefined
                  : String(batchUniform)
              }
              onChange={(value) => setBatchUniform(value)}
            />
          ) : (
            <InputNumber
              min={0}
              precision={2}
              addonBefore="US$"
              addonAfter={priceUnitSuffix}
              style={{ width: 200 }}
              value={
                batchUniform === undefined || batchUniform === null
                  ? undefined
                  : Number(batchUniform)
              }
              onChange={(value) => setBatchUniform(value)}
            />
          )}
          <Button type="primary" onClick={applyUniformToDrafts}>
            {'应用到全部'}
          </Button>
        </Space>
        <ProTable<DhProductSkuPublic>
          rowKey={skuRowKey}
          search={false}
          options={false}
          toolBarRender={false}
          pagination={false}
          dataSource={batchDrafts}
          columns={batchModalColumns}
          size="small"
          bordered
          scroll={{
            x: Math.max(640, attrColumns.length * 120 + 220),
            y: 360,
          }}
        />
      </Modal>
    </>
  );
};

export default SpecSkuTable;
