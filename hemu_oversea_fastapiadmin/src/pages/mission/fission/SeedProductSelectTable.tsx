import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { useIntl, useModel } from '@umijs/max';
import { App, Button, Image, Space, Typography } from 'antd';
import type { CascaderProps, DefaultOptionType } from 'antd/es/cascader';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import { DH_PRODUCT_STATE_LABEL, DH_PRODUCT_STATES } from '@/constants/product';
import { formatSyncState } from '@/pages/product/utils';
import { fetchDhSeedCategories } from '@/services/admin/categories';
import { fetchDhProductList } from '@/services/admin/products';
import { fetchStoreList } from '@/services/admin/stores';
import type {
  DhProductPublic,
  DhSeedCategoryPublic,
  StorePublic,
} from '@/types/api';
import { formatDateTime } from '@/utils/datetime';

type ProductTableParams = {
  current?: number;
  pageSize?: number;
  state?: string;
  item_code?: string;
  item_name?: string;
  store_id?: number | string;
  cate_pub_id?: string | string[];
};

type SeedCategoryOption = DefaultOptionType & {
  isLeaf?: boolean;
  loading?: boolean;
  children?: SeedCategoryOption[];
};

function categoryTitle(item: DhSeedCategoryPublic): string {
  const cn = item.pub_name_cn?.trim();
  if (cn) {
    return cn;
  }
  return item.pub_name;
}

function toSeedCategoryOption(item: DhSeedCategoryPublic): SeedCategoryOption {
  return {
    value: item.cate_pub_id,
    label: `${categoryTitle(item)}（${item.product_count}）`,
    isLeaf: item.is_leaf,
  };
}

function updateCascaderChildren(
  list: SeedCategoryOption[],
  targetValue: string,
  children: SeedCategoryOption[],
): SeedCategoryOption[] {
  return list.map((node) => {
    if (node.value === targetValue) {
      return {
        ...node,
        loading: false,
        children,
        isLeaf: children.length === 0 ? true : node.isLeaf,
      };
    }
    if (node.children?.length) {
      return {
        ...node,
        children: updateCascaderChildren(node.children, targetValue, children),
      };
    }
    return node;
  });
}

function resolveCatePubId(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) {
    const last = value.filter(Boolean).at(-1);
    return last || undefined;
  }
  const text = value?.trim();
  return text || undefined;
}

export function SeedProductSelectTable({
  selectedId,
  onSelect,
}: {
  selectedId?: number;
  onSelect: (product: DhProductPublic) => void;
}) {
  const intl = useIntl();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const supplierId = initialState?.currentUser?.supplier_id;
  const actionRef = useRef<ActionType | null>(null);
  const [stores, setStores] = useState<StorePublic[]>([]);
  const [categoryOptions, setCategoryOptions] = useState<SeedCategoryOption[]>(
    [],
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const items = await fetchDhSeedCategories({});
        if (!cancelled) {
          setCategoryOptions(items.map(toSeedCategoryOption));
        }
      } catch (error) {
        if (!cancelled) {
          setCategoryOptions([]);
          message.error(
            error instanceof Error
              ? error.message
              : intl.formatMessage({
                  id: 'pages.product.list.loadCategoriesFailed',
                  defaultMessage: '加载商品分类失败',
                }),
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [intl, message]);

  const loadCategoryData: CascaderProps<SeedCategoryOption>['loadData'] = (
    selectedOptions,
  ) => {
    const targetOption = selectedOptions[selectedOptions.length - 1];
    if (!targetOption || targetOption.isLeaf || targetOption.children) {
      return;
    }

    targetOption.loading = true;
    setCategoryOptions((prev) => [...prev]);

    void (async () => {
      try {
        const items = await fetchDhSeedCategories({
          parent_id: String(targetOption.value),
        });
        setCategoryOptions((prev) =>
          updateCascaderChildren(
            prev,
            String(targetOption.value),
            items.map(toSeedCategoryOption),
          ),
        );
      } catch (error) {
        targetOption.loading = false;
        setCategoryOptions((prev) => [...prev]);
        message.error(
          error instanceof Error
            ? error.message
            : intl.formatMessage({
                id: 'pages.product.list.loadCategoriesFailed',
                defaultMessage: '加载商品分类失败',
              }),
        );
      }
    })();
  };

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
    () => Object.fromEntries(stores.map((store) => [store.id, store.name])),
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
        id: 'pages.product.list.field.category',
        defaultMessage: '商品分类',
      }),
      dataIndex: 'cate_pub_id',
      hideInTable: true,
      valueType: 'cascader',
      fieldProps: {
        options: categoryOptions,
        loadData: loadCategoryData,
        changeOnSelect: true,
        allowClear: true,
        placeholder: intl.formatMessage({
          id: 'pages.product.list.field.categoryPlaceholder',
          defaultMessage: '全部',
        }),
        styles: { popup: { listItem: { width: 180, maxWidth: 180 } } },
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
            <Typography.Paragraph
              ellipsis={{ rows: 2, tooltip: record.item_name || undefined }}
              style={{ marginBottom: 4 }}
            >
              {record.item_name || '-'}
            </Typography.Paragraph>
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
        id: 'pages.product.detail.field.syncState',
        defaultMessage: '同步状态',
      }),
      dataIndex: 'sync_state',
      search: false,
      width: 100,
      render: (_, record) =>
        formatSyncState(
          record.sync_state,
          intl.formatMessage({
            id: 'pages.product.detail.sync.success',
            defaultMessage: '成功',
          }),
          intl.formatMessage({
            id: 'pages.product.detail.sync.fail',
            defaultMessage: '失败',
          }),
        ),
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
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.option',
        defaultMessage: '操作',
      }),
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 96,
      fixed: 'right',
      render: (_, record) => {
        const selected = record.id === selectedId;
        return [
          <Button type="link" key="select" onClick={() => onSelect(record)}>
            {intl.formatMessage({
              id: selected
                ? 'pages.mission.add.selected'
                : 'pages.mission.add.select',
              defaultMessage: selected ? '已选择' : '选择',
            })}
          </Button>,
        ];
      },
    },
  ];

  return (
    <div onSubmit={(event) => event.stopPropagation()}>
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
        scroll={{ x: 1020 }}
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
          const catePubId = resolveCatePubId(params.cate_pub_id);
          const data = await fetchDhProductList({
            type: 1,
            state: params.state?.trim() || undefined,
            item_code: params.item_code?.trim() || undefined,
            item_name: params.item_name?.trim() || undefined,
            store_id:
              storeId !== undefined && Number.isInteger(storeId) && storeId > 0
                ? storeId
                : undefined,
            cate_pub_id: catePubId,
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
    </div>
  );
}
