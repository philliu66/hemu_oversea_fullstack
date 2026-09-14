import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useIntl, useModel } from '@umijs/max';
import { App, Image, Space, Typography } from 'antd';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import { DH_PRODUCT_STATE_LABEL, DH_PRODUCT_STATES } from '@/constants/product';
import { fetchDhProductList } from '@/services/admin/products';
import { fetchStoreList } from '@/services/admin/stores';
import type { DhProductPublic, StorePublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { productDetailPath } from '../utils';

type ProductTableParams = {
  current?: number;
  pageSize?: number;
  state?: string;
  item_code?: string;
  item_name?: string;
  store_id?: number | string;
};

function formatPrice(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  const num = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(num)) {
    return String(value);
  }
  return num.toFixed(2);
}

function formatPriceRange(
  min: string | number | null | undefined,
  max: string | number | null | undefined,
): string {
  const minText = formatPrice(min);
  const maxText = formatPrice(max);
  if (minText === '-' && maxText === '-') {
    return '-';
  }
  if (minText === maxText) {
    return minText;
  }
  return `${minText} ~ ${maxText}`;
}

const ProductList: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const supplierId = initialState?.currentUser?.supplier_id;
  const actionRef = useRef<ActionType | null>(null);
  const [stores, setStores] = useState<StorePublic[]>([]);

  useEffect(() => {
    if (!supplierId) {
      setStores([]);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchStoreList({
          supplier_id: supplierId,
          page: 1,
          page_size: 100,
        });
        if (!cancelled) {
          setStores(data.items);
        }
      } catch (error) {
        if (!cancelled) {
          setStores([]);
          message.error(
            error instanceof Error
              ? error.message
              : intl.formatMessage({
                  id: 'pages.product.list.loadStoresFailed',
                  defaultMessage: '加载店铺列表失败',
                }),
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [intl, message, supplierId]);

  const storeValueEnum = useMemo(
    () =>
      Object.fromEntries(
        stores.map((store) => [
          String(store.id),
          {
            text: store.name,
          },
        ]),
      ),
    [stores],
  );

  const storeNameMap = useMemo(
    () =>
      Object.fromEntries(
        stores.map((store) => [store.id, store.name]),
      ) as Record<number, string>,
    [stores],
  );

  const stateValueEnum = useMemo(
    () =>
      Object.fromEntries(
        DH_PRODUCT_STATES.map((code) => [
          code,
          {
            text: intl.formatMessage({
              id: `pages.product.list.state.${code}`,
              defaultMessage: DH_PRODUCT_STATE_LABEL[code],
            }),
          },
        ]),
      ),
    [intl],
  );

  const columns: ProColumns<DhProductPublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.itemCode',
        defaultMessage: '商品编码',
      }),
      dataIndex: 'item_code',
      hideInTable: true,
      fieldProps: {
        placeholder: intl.formatMessage({
          id: 'pages.product.list.field.itemCodePlaceholder',
          defaultMessage: '精确匹配',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.itemName',
        defaultMessage: '商品标题',
      }),
      dataIndex: 'item_name',
      hideInTable: true,
      fieldProps: {
        placeholder: intl.formatMessage({
          id: 'pages.product.list.field.itemNamePlaceholder',
          defaultMessage: '模糊匹配',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.store',
        defaultMessage: '店铺',
      }),
      dataIndex: 'store_id',
      hideInTable: true,
      valueType: 'select',
      valueEnum: storeValueEnum,
      fieldProps: {
        allowClear: true,
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: intl.formatMessage({
          id: 'pages.product.list.field.storePlaceholder',
          defaultMessage: '请选择店铺',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.state',
        defaultMessage: '状态',
      }),
      dataIndex: 'state',
      hideInTable: true,
      valueType: 'select',
      valueEnum: stateValueEnum,
      fieldProps: {
        allowClear: true,
        placeholder: intl.formatMessage({
          id: 'pages.product.list.field.statePlaceholder',
          defaultMessage: '请选择状态',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.product',
        defaultMessage: '商品',
      }),
      dataIndex: 'product',
      search: false,
      width: 320,
      render: (_, record) => (
        <Space align="start" size={12} style={{ maxWidth: '100%' }}>
          {record.main_image_url ? (
            <Image
              src={record.main_image_url}
              alt={record.item_name || record.item_code}
              width={48}
              height={48}
              style={{
                objectFit: 'cover',
                borderRadius: 6,
                flexShrink: 0,
              }}
            />
          ) : (
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 6,
                background: 'rgba(0,0,0,0.04)',
                flexShrink: 0,
              }}
            />
          )}
          <div style={{ minWidth: 0, flex: 1 }}>
            <Typography.Link
              onClick={() => history.push(productDetailPath(record.id))}
              style={{ display: 'block', marginBottom: 4 }}
            >
              <Typography.Paragraph
                ellipsis={{ rows: 2, tooltip: record.item_name || undefined }}
                style={{ marginBottom: 0, color: 'inherit' }}
              >
                {record.item_name || '-'}
              </Typography.Paragraph>
            </Typography.Link>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {record.item_code}
            </Typography.Text>
          </div>
        </Space>
      ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.store',
        defaultMessage: '店铺',
      }),
      dataIndex: 'store_name',
      search: false,
      width: 140,
      ellipsis: true,
      render: (_, record) =>
        storeNameMap[record.store_id] || String(record.store_id),
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.state',
        defaultMessage: '状态',
      }),
      dataIndex: 'state',
      search: false,
      width: 140,
      ellipsis: true,
      render: (_, record) => record.state || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.price',
        defaultMessage: '价格',
      }),
      dataIndex: 'price_min',
      search: false,
      width: 120,
      render: (_, record) =>
        formatPriceRange(record.price_min, record.price_max),
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.skuCount',
        defaultMessage: 'SKU 数量',
      }),
      dataIndex: 'sku_count',
      search: false,
      width: 96,
      align: 'right',
      render: (_, record) =>
        record.sku_count === null || record.sku_count === undefined
          ? '-'
          : record.sku_count,
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.lastSyncedAt',
        defaultMessage: '同步时间',
      }),
      dataIndex: 'last_synced_at',
      search: false,
      width: 168,
      render: (_, record) => formatDateTime(record.last_synced_at),
    },
  ];

  return (
    <PageContainer>
      <ProTable<DhProductPublic, ProductTableParams>
        headerTitle={intl.formatMessage({
          id: 'pages.product.list.title',
          defaultMessage: '商品列表',
        })}
        actionRef={actionRef}
        rowKey="id"
        size="middle"
        cardBordered
        search={{
          labelWidth: 72,
          span: 8,
          defaultCollapsed: false,
        }}
        options={false}
        scroll={{ x: 1000 }}
        pagination={{
          defaultPageSize: PAGE_SIZE_DEFAULT,
          showSizeChanger: true,
          showTotal: (total) =>
            intl.formatMessage(
              {
                id: 'pages.product.list.total',
                defaultMessage: '共 {total} 条',
              },
              { total },
            ),
        }}
        columns={columns}
        request={async (params) => {
          const storeIdRaw = params.store_id;
          const storeId =
            storeIdRaw === undefined || storeIdRaw === null || storeIdRaw === ''
              ? undefined
              : Number(storeIdRaw);

          const data = await fetchDhProductList({
            type: 1,
            state: params.state?.trim() || undefined,
            item_code: params.item_code?.trim() || undefined,
            item_name: params.item_name?.trim() || undefined,
            store_id:
              storeId !== undefined && Number.isInteger(storeId) && storeId > 0
                ? storeId
                : undefined,
            sort: 0,
            page: params.current ?? 1,
            page_size: params.pageSize ?? PAGE_SIZE_DEFAULT,
          });
          return {
            data: data.items,
            total: data.total,
            success: true,
          };
        }}
      />
    </PageContainer>
  );
};

export default ProductList;
