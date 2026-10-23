import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useAccess, useModel } from '@umijs/max';
import {
  App,
  Button,
  Image,
  Input,
  Modal,
  Popconfirm,
  Popover,
  Progress,
  Select,
  Space,
  Typography,
} from 'antd';
import type { CascaderProps, DefaultOptionType } from 'antd/es/cascader';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { buildPlatformSupplierSearchColumn } from '@/components/SupplierSelectField';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import { DH_PRODUCT_STATE_LABEL, DH_PRODUCT_STATES } from '@/constants/product';
import { fetchDhSeedCategories } from '@/services/admin/categories';
import {
  fetchDhProductList,
  syncDhProduct,
} from '@/services/admin/products';
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
  productDetailPath,
  productEditPath,
} from '../utils';

function parseItemCodes(raw: string): string[] {
  const seen = new Set<string>();
  const codes: string[] = [];
  for (const part of raw.split(/[,，]/)) {
    const code = part.trim();
    if (!code || seen.has(code)) {
      continue;
    }
    seen.add(code);
    codes.push(code);
  }
  return codes;
}

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
  const [createPopoverOpen, setCreatePopoverOpen] = useState(false);
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [syncStoreId, setSyncStoreId] = useState<number>();
  const [syncItemCodesText, setSyncItemCodesText] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncDone, setSyncDone] = useState(0);
  const [syncTotal, setSyncTotal] = useState(0);
  const [rowSyncingId, setRowSyncingId] = useState<number>();

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
          buildPlatformSupplierSearchColumn<DhProductPublic>({
            onChange: (v) => {
              setSelectedSupplierId(v);
              actionRef.current?.reload();
            },
          }),
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
              onClick={() => {
                const sid = supplierId ?? record.supplier_id ?? undefined;
                history.push(
                  access.canWriteSupplierData
                    ? productEditPath(record.id, { supplierId: sid })
                    : productDetailPath(record.id, { supplierId: sid }),
                );
              }}
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
      title: '同步',
      dataIndex: 'sync',
      search: false,
      width: 168,
      render: (_, record) => (
        <div style={{ lineHeight: 1.4 }}>
          <div>
            {formatSyncState(record.sync_state, '成功', '失败')}
          </div>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {formatDateTime(record.last_synced_at) || '-'}
          </Typography.Text>
        </div>
      ),
    },
    {
      title: '操作',
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 220,
      fixed: 'right',
      render: (_, record) => {
        const sid = supplierId ?? record.supplier_id ?? undefined;
        const actions: React.ReactNode[] = [
          <Button
            key="detail"
            color="default"
            variant="filled"
            size="small"
            shape="round"
            onClick={() =>
              history.push(productDetailPath(record.id, { supplierId: sid }))
            }
          >
            查看详情
          </Button>,
        ];
        if (
          access.canWriteSupplierData &&
          access.can('product.list.sync')
        ) {
          actions.push(
            <Popconfirm
              key="sync"
              title="确认同步该商品数据？"
              disabled={rowSyncingId === record.id || syncing}
              onConfirm={async () => {
                setRowSyncingId(record.id);
                try {
                  const result = await syncDhProduct({
                    store_id: record.store_id,
                    item_code: record.item_code,
                  });
                  if (result.ok) {
                    message.success('同步成功');
                    actionRef.current?.reload();
                  } else {
                    message.error(result.message || '同步失败');
                    actionRef.current?.reload();
                  }
                } catch {
                  // 错误已由全局拦截器处理
                } finally {
                  setRowSyncingId(undefined);
                }
              }}
            >
              <Button
                type="primary"
                size="small"
                shape="round"
                loading={rowSyncingId === record.id}
                disabled={syncing}
              >
                同步商品
              </Button>
            </Popconfirm>,
          );
        }
        return (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, max-content)',
              gap: 8,
              justifyContent: 'start',
            }}
          >
            {actions}
          </div>
        );
      },
    },
  ];

  const openSyncModal = () => {
    setCreatePopoverOpen(false);
    setSyncStoreId(undefined);
    setSyncItemCodesText('');
    setSyncing(false);
    setSyncDone(0);
    setSyncTotal(0);
    setSyncModalOpen(true);
  };

  const handleManualCreate = () => {
    setCreatePopoverOpen(false);
    history.push(
      productCreatePath({
        supplierId: supplierId,
      }),
    );
  };

  const handleStartSync = async () => {
    if (!syncStoreId) {
      message.warning('请选择店铺');
      return;
    }
    const codes = parseItemCodes(syncItemCodesText);
    if (!codes.length) {
      message.warning('请输入至少一个商品编码');
      return;
    }

    setSyncing(true);
    setSyncTotal(codes.length);
    setSyncDone(0);
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < codes.length; i += 1) {
      const itemCode = codes[i];
      try {
        const result = await syncDhProduct(
          { store_id: syncStoreId, item_code: itemCode },
          { skipErrorHandler: true },
        );
        if (result.ok) {
          successCount += 1;
        } else {
          failCount += 1;
        }
      } catch {
        failCount += 1;
      }
      setSyncDone(i + 1);
    }

    setSyncing(false);
    setSyncModalOpen(false);
    actionRef.current?.reload();
    const tip = `同步完成：成功 ${successCount} 个，失败 ${failCount} 个`;
    if (failCount > 0 && successCount > 0) {
      message.warning(tip);
    } else if (failCount > 0) {
      message.error(tip);
    } else {
      message.success(tip);
    }
  };

  const syncPercent =
    syncTotal > 0 ? Math.round((syncDone / syncTotal) * 100) : 0;

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
        toolBarRender={() =>
          access.canWriteSupplierData
            ? [
                <Popover
                  key="create"
                  trigger="click"
                  open={createPopoverOpen}
                  onOpenChange={setCreatePopoverOpen}
                  placement="bottomLeft"
                  content={
                    <Space direction="vertical" style={{ minWidth: 120 }}>
                      <Button type="link" onClick={handleManualCreate}>
                        手动新建
                      </Button>
                      {access.can('product.list.sync') ? (
                        <Button type="link" onClick={openSyncModal}>
                          敦煌同步
                        </Button>
                      ) : null}
                    </Space>
                  }
                >
                  <Button type="primary" icon={<PlusOutlined />}>
                    {'新建'}
                  </Button>
                </Popover>,
              ]
            : []
        }
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
      <Modal
        title="敦煌同步"
        open={syncModalOpen}
        centered
        destroyOnClose
        maskClosable={false}
        keyboard={!syncing}
        closable={!syncing}
        onCancel={() => {
          if (!syncing) {
            setSyncModalOpen(false);
          }
        }}
        footer={
          syncing
            ? null
            : [
                <Button key="cancel" onClick={() => setSyncModalOpen(false)}>
                  取消
                </Button>,
                <Button key="ok" type="primary" onClick={() => void handleStartSync()}>
                  开始同步
                </Button>,
              ]
        }
      >
        {syncing ? (
          <div style={{ paddingTop: 8 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
              }}
            >
              <Progress
                percent={syncPercent}
                status="active"
                style={{ flex: 1, marginBottom: 0 }}
                showInfo={false}
              />
              <Typography.Text style={{ whiteSpace: 'nowrap' }}>
                {`${syncDone}/${syncTotal}`}
              </Typography.Text>
            </div>
            <Typography.Text type="secondary" style={{ marginTop: 12, display: 'block' }}>
              正在同步敦煌商品，请稍候…
            </Typography.Text>
          </div>
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <div>
              <Typography.Text style={{ display: 'block', marginBottom: 8 }}>
                店铺
              </Typography.Text>
              <Select
                style={{ width: '100%' }}
                placeholder="请选择店铺"
                value={syncStoreId}
                onChange={(value) => setSyncStoreId(value)}
                options={stores.map((store) => ({
                  value: store.id,
                  label: store.name,
                }))}
                showSearch
                optionFilterProp="label"
              />
            </div>
            <div>
              <Typography.Text style={{ display: 'block', marginBottom: 8 }}>
                产品编码
              </Typography.Text>
              <Input.TextArea
                rows={4}
                value={syncItemCodesText}
                onChange={(e) => setSyncItemCodesText(e.target.value)}
                placeholder="可输入多个编码，用逗号,分割批量同步"
              />
            </div>
          </Space>
        )}
      </Modal>
    </PageContainer>
  );
};

export default ProductList;
