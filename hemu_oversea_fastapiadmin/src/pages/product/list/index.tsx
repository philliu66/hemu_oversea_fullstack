import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useAccess, useModel } from '@umijs/max';
import { App, Button, Image, Space, Typography } from 'antd';
import type { CascaderProps, DefaultOptionType } from 'antd/es/cascader';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import SupplierSelectField from '@/components/SupplierSelectField';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import { DH_PRODUCT_STATE_LABEL, DH_PRODUCT_STATES } from '@/constants/product';
import { fetchDhSeedCategories } from '@/services/admin/categories';
import { fetchDhProductList } from '@/services/admin/products';
import { fetchStoreList } from '@/services/admin/stores';
import type {
  DhProductPublic,
  DhSeedCategoryPublic,
  StorePublic,
} from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import {
  needsSupplierSelection,
  resolveRequestSupplierId,
} from '@/utils/portalScope';
import {
  formatSyncState,
  productCreatePath,
  productEditPath,
} from '../utils';

type ProductTableParams = {
  current?: number;
  pageSize?: number;
  state?: string;
  item_code?: string;
  item_name?: string;
  store_id?: number | string;
  cate_pub_id?: string | string[];
  supplier_id?: number;
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

const ProductList: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();
  const supplierId = resolveRequestSupplierId(currentUser, selectedSupplierId);
  const actionRef = useRef<ActionType | null>(null);
  const [stores, setStores] = useState<StorePublic[]>([]);
  const [categoryOptions, setCategoryOptions] = useState<SeedCategoryOption[]>(
    [],
  );

  useEffect(() => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      setCategoryOptions([]);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const items = await fetchDhSeedCategories({ supplier_id: supplierId });
        if (!cancelled) {
          setCategoryOptions(items.map(toSeedCategoryOption));
        }
      } catch (error) {
        if (!cancelled) {
          setCategoryOptions([]);
          message.error(
            error instanceof Error
              ? error.message
              : '加载商品分类失败',
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [currentUser, message, supplierId]);

  const loadCategoryData: CascaderProps<SeedCategoryOption>['loadData'] = (
    selectedOptions,
  ) => {
    const targetOption = selectedOptions[selectedOptions.length - 1];
    if (!targetOption || targetOption.isLeaf || targetOption.children) {
      return;
    }
    if (!supplierId) {
      return;
    }

    targetOption.loading = true;
    setCategoryOptions((prev) => [...prev]);

    void (async () => {
      try {
        const items = await fetchDhSeedCategories({
          parent_id: String(targetOption.value),
          supplier_id: supplierId,
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
            : '加载商品分类失败',
        );
      }
    })();
  };

  useEffect(() => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
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
              : '加载店铺列表失败',
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [currentUser, message, supplierId]);

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

  const stateValueEnum = useMemo(
    () =>
      Object.fromEntries(
        DH_PRODUCT_STATES.map((code) => [
          code,
          {
            text: DH_PRODUCT_STATE_LABEL[code],
          },
        ]),
      ),
    [],
  );

  const columns: ProColumns<DhProductPublic>[] = [
    ...(access.canPlatform
      ? [
          {
            title: '供应商',
            dataIndex: 'supplier_id',
            hideInTable: true,
            order: 100,
            renderFormItem: () => (
              <SupplierSelectField
                value={selectedSupplierId}
                onChange={(v) => {
                  setSelectedSupplierId(v);
                  actionRef.current?.reload();
                }}
              />
            ),
          } as ProColumns<DhProductPublic>,
          {
            title: '供应商',
            dataIndex: 'supplier_name',
            search: false,
            width: 140,
            ellipsis: true,
            render: (_, record) => record.supplier_name || '-',
          } as ProColumns<DhProductPublic>,
        ]
      : []),
    {
      title: '商品编码',
      dataIndex: 'item_code',
      hideInTable: true,
      fieldProps: {
        placeholder: '精确匹配',
      },
    },
    {
      title: '商品标题',
      dataIndex: 'item_name',
      hideInTable: true,
      fieldProps: {
        placeholder: '模糊匹配',
      },
    },
    {
      title: '商品分类',
      dataIndex: 'cate_pub_id',
      hideInTable: true,
      valueType: 'cascader',
      fieldProps: {
        options: categoryOptions,
        loadData: loadCategoryData,
        changeOnSelect: true,
        allowClear: true,
        placeholder: '全部',
        styles: { popup: { listItem: { width: 180, maxWidth: 180 } } },
      },
    },
    {
      title: '店铺',
      dataIndex: 'store_id',
      hideInTable: true,
      valueType: 'select',
      valueEnum: storeValueEnum,
      fieldProps: {
        allowClear: true,
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择店铺',
      },
    },
    {
      title: '状态',
      dataIndex: 'state',
      hideInTable: true,
      valueType: 'select',
      valueEnum: stateValueEnum,
      fieldProps: {
        allowClear: true,
        placeholder: '请选择状态',
      },
    },
    {
      title: '商品',
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
              onClick={() =>
                history.push(
                  productEditPath(record.id, {
                    supplierId: supplierId ?? record.supplier_id ?? undefined,
                  }),
                )
              }
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
      title: '店铺',
      dataIndex: 'store_name',
      search: false,
      width: 140,
      ellipsis: true,
      render: (_, record) => record.store_name || '-',
    },
    {
      title: '状态',
      dataIndex: 'state',
      search: false,
      width: 140,
      ellipsis: true,
      render: (_, record) => record.state || '-',
    },
    {
      title: '同步状态',
      dataIndex: 'sync_state',
      search: false,
      width: 100,
      render: (_, record) =>
        formatSyncState(
          record.sync_state,
          '成功',
          '失败',
        ),
    },
    {
      title: '同步时间',
      dataIndex: 'last_synced_at',
      search: false,
      width: 168,
      render: (_, record) => formatDateTime(record.last_synced_at),
    },
    // 操作列暂时隐藏，进入商品只保留点击标题进入编辑。
    // 恢复时需重新引入 productDetailPath、productCreatePath。
    // {
    //   title: '操作',
    //   dataIndex: 'option',
    //   valueType: 'option',
    //   search: false,
    //   width: 200,
    //   fixed: 'right',
    //   render: (_, record) => [
    //     <Button type="link" key="detail" onClick={() => history.push(productDetailPath(record.id))}>
    //       {'查看'}
    //     </Button>,
    //     <Button type="link" key="edit" onClick={() => history.push(productEditPath(record.id))}>
    //       {'编辑'}
    //     </Button>,
    //     <Button type="link" key="copy" onClick={() => history.push(productCreatePath({ from: record.id }))}>
    //       {'复制'}
    //     </Button>,
    //   ],
    // },
  ];

  return (
    <PageContainer>
      <ProTable<DhProductPublic, ProductTableParams>
        headerTitle={'商品列表'}
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
        scroll={{ x: 960 }}
        toolBarRender={() => [
          <Button
            type="primary"
            key="create"
            icon={<PlusOutlined />}
            onClick={() =>
              history.push(
                productCreatePath({
                  supplierId: supplierId,
                }),
              )
            }
          >
            {'新建'}
          </Button>,
        ]}
        pagination={{
          defaultPageSize: PAGE_SIZE_DEFAULT,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        columns={columns}
        request={async (params) => {
          const scopedSupplierId = resolveRequestSupplierId(
            currentUser,
            params.supplier_id ?? selectedSupplierId,
          );
          if (needsSupplierSelection(currentUser, scopedSupplierId)) {
            return { data: [], success: true, total: 0 };
          }
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
            supplier_id: scopedSupplierId,
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
