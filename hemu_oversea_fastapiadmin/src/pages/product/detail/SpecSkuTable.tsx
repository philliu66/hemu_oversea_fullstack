import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import {
  Button,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Typography,
} from 'antd';
import React, { useMemo, useState } from 'react';
import type {
  DhProductSelectedAttrPublic,
  DhProductSkuPublic,
  DhProductSpecSelfDefPublic,
} from '@/types/api';

const CUSTOM_SPEC_COL = '__custom_spec__';

type SpecSkuTableProps = {
  skuList?: DhProductSkuPublic[];
  priceSelectedAttrs?: DhProductSelectedAttrPublic[];
  specSelfDefs?: DhProductSpecSelfDefPublic[];
  itemCode?: string | null;
  /** 价格列单位后缀，联动计件单位（如 套） */
  measureUnitLabel?: string;
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

const SpecSkuTable: React.FC<SpecSkuTableProps> = ({
  skuList,
  priceSelectedAttrs,
  specSelfDefs,
  itemCode,
  measureUnitLabel,
  disabled = false,
  onChange,
}) => {
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
            <Button
              type="link"
              size="small"
              style={{ paddingInline: 4 }}
              onClick={() => openBatchModal('retail_price')}
            >
              {'批量设置'}
            </Button>
          ) : null}
        </Space>
      ),
      dataIndex: 'retail_price',
      width: 200,
      search: false,
      render: (_, record, index) => {
        const num =
          record.retail_price === null || record.retail_price === undefined
            ? undefined
            : Number(record.retail_price);
        return (
          <InputNumber
            value={Number.isFinite(num) ? num : undefined}
            min={0}
            precision={2}
            disabled={disabled}
            addonBefore="US$"
            addonAfter={priceUnitSuffix}
            style={{ width: '100%' }}
            onChange={(value) =>
              patchSku(index, {
                retail_price: value == null ? null : value,
              })
            }
          />
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
