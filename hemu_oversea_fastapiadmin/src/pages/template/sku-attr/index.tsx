import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import { App, Button, Popconfirm, Space } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { buildPlatformSupplierSearchColumn } from '@/components/SupplierSelectField';
import CategorySelectField, {
  formatCategoryPathDisplay,
} from '@/pages/product/detail/CategorySelectField';
import { fetchDhCategoryPath } from '@/services/admin/categories';
import { fetchSkuBaseInfoList } from '@/services/admin/sku';
import {
  deleteSkuAttrTemplate,
  fetchSkuAttrTemplateList,
} from '@/services/admin/templates';
import type {
  DhCategoryPublic,
  SkuAttrTemplateListItemPublic,
} from '@/types/api';
import {
  needsSupplierSelection,
  resolveRequestSupplierId,
} from '@/utils/portalScope';
import SkuAttrTemplateDrawer, {
  type SkuAttrDrawerMode,
} from './SkuAttrTemplateDrawer';

type TableParams = {
  sku_code?: string;
  supplier_id?: number;
};

const SkuAttrTemplatePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const actionRef = useRef<ActionType>(null);
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();
  const supplierId = resolveRequestSupplierId(currentUser, selectedSupplierId);

  const [skuOptions, setSkuOptions] = useState<
    { label: string; value: string }[]
  >([]);
  const [skuOptionsLoading, setSkuOptionsLoading] = useState(false);
  const [searchCategory, setSearchCategory] = useState<DhCategoryPublic | null>(
    null,
  );
  const [searchCategoryPath, setSearchCategoryPath] = useState<
    string | undefined
  >();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<SkuAttrDrawerMode>('create');
  const [drawerTemplateId, setDrawerTemplateId] = useState<number | null>(null);

  useEffect(() => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      setSkuOptions([]);
      return;
    }
    let cancelled = false;
    setSkuOptionsLoading(true);
    void fetchSkuBaseInfoList({
      page: 1,
      page_size: 5000,
      supplier_id: supplierId,
    })
      .then((data) => {
        if (cancelled) {
          return;
        }
        setSkuOptions(
          (data.items || []).map((item) => ({
            label: item.sku_code,
            value: item.sku_code,
          })),
        );
      })
      .catch((error) => {
        if (!cancelled) {
          message.error(
            error instanceof Error ? error.message : '加载产品型号失败',
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setSkuOptionsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [currentUser, message, supplierId]);

  const openCreate = () => {
    if (needsSupplierSelection(currentUser, supplierId)) {
      message.warning('请先选择供应商');
      return;
    }
    setDrawerMode('create');
    setDrawerTemplateId(null);
    setDrawerOpen(true);
  };

  const openView = (row: SkuAttrTemplateListItemPublic) => {
    setDrawerMode('view');
    setDrawerTemplateId(row.id);
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setDrawerTemplateId(null);
  };

  const columns: ProColumns<SkuAttrTemplateListItemPublic>[] = [
    ...(access.canPlatform
      ? [
          buildPlatformSupplierSearchColumn<SkuAttrTemplateListItemPublic>({
            onChange: (v) => {
              setSelectedSupplierId(v);
              actionRef.current?.reload();
            },
          }),
          {
            title: '供应商',
            dataIndex: 'supplier_name',
            search: false,
            width: 160,
            ellipsis: true,
            render: (_, record) => record.supplier_name || '-',
          } as ProColumns<SkuAttrTemplateListItemPublic>,
        ]
      : []),
    {
      title: '产品型号',
      dataIndex: 'sku_code',
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        allowClear: true,
        options: skuOptions,
        loading: skuOptionsLoading,
        optionFilterProp: 'label',
        placeholder: '请选择产品型号',
      },
      width: 200,
      ellipsis: true,
    },
    {
      title: '分类名称',
      dataIndex: 'cate_pub_id',
      hideInTable: true,
      renderFormItem: () => (
        <CategorySelectField
          category={searchCategory}
          pathDisplay={searchCategoryPath}
          onPick={(category) => {
            setSearchCategory(category);
            void fetchDhCategoryPath(category.id)
              .then((pathData) => {
                setSearchCategoryPath(formatCategoryPathDisplay(pathData));
              })
              .catch(() => {
                setSearchCategoryPath(undefined);
              });
          }}
        />
      ),
    } as ProColumns<SkuAttrTemplateListItemPublic>,
    {
      title: '分类名称',
      dataIndex: 'cate_name',
      search: false,
      ellipsis: true,
      render: (_, record) => record.cate_name || record.cate_pub_id || '-',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      search: false,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => openView(record)}>
            查看属性
          </Button>
          {access.canWriteSupplierData ? (
            <Popconfirm
              title="确认删除该属性模板？"
              onConfirm={async () => {
                try {
                  await deleteSkuAttrTemplate(record.id, {
                    supplier_id:
                      resolveRequestSupplierId(
                        currentUser,
                        record.supplier_id ?? selectedSupplierId,
                      ) ?? undefined,
                  });
                  message.success('删除成功');
                  void actionRef.current?.reload();
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button type="link" size="small" danger>
                删除
              </Button>
            </Popconfirm>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<SkuAttrTemplateListItemPublic, TableParams>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
        toolBarRender={() =>
          access.canWriteSupplierData
            ? [
                <Button key="create" type="primary" onClick={openCreate}>
                  新增
                </Button>,
              ]
            : []
        }
        onReset={() => {
          setSearchCategory(null);
          setSearchCategoryPath(undefined);
        }}
        request={async (params) => {
          const scopedSupplierId = resolveRequestSupplierId(
            currentUser,
            params.supplier_id ?? selectedSupplierId,
          );
          if (needsSupplierSelection(currentUser, scopedSupplierId)) {
            return { data: [], success: true, total: 0 };
          }
          try {
            const data = await fetchSkuAttrTemplateList({
              sku_code: params.sku_code,
              cate_pub_id: searchCategory?.cate_pub_id,
              page: params.current,
              page_size: params.pageSize,
              supplier_id: scopedSupplierId,
            });
            return {
              data: data.items,
              success: true,
              total: data.total,
            };
          } catch (error) {
            message.error(
              error instanceof Error ? error.message : '加载列表失败',
            );
            return {
              data: [],
              success: false,
              total: 0,
            };
          }
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
      />
      <SkuAttrTemplateDrawer
        open={drawerOpen}
        mode={drawerMode}
        templateId={drawerTemplateId}
        supplierId={supplierId}
        skuOptions={skuOptions}
        skuOptionsLoading={skuOptionsLoading}
        onClose={closeDrawer}
        onModeChange={setDrawerMode}
        onSaved={() => {
          void actionRef.current?.reload();
        }}
      />
    </PageContainer>
  );
};

export default SkuAttrTemplatePage;
