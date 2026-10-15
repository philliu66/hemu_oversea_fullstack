import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess } from '@umijs/max';
import { App, Button, Popconfirm } from 'antd';
import React, { useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import { deleteSupplier, fetchSupplierList } from '@/services/admin/suppliers';
import type { SupplierPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import {
  SupplierFormDrawer,
  type SupplierDrawerMode,
} from './SupplierFormDrawer';

type SupplierTableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
};

const SupplierList: React.FC = () => {
  const access = useAccess();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<SupplierDrawerMode>('create');
  const [activeId, setActiveId] = useState<number>();

  const canCreate = access.can('supplier.create');
  const canUpdate = access.can('supplier.update');
  const canDelete = access.can('supplier.delete');

  const openCreate = () => {
    setActiveId(undefined);
    setDrawerMode('create');
    setDrawerOpen(true);
  };

  const openView = (id: number) => {
    setActiveId(id);
    setDrawerMode('view');
    setDrawerOpen(true);
  };

  const openEdit = (id: number) => {
    setActiveId(id);
    setDrawerMode('edit');
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setActiveId(undefined);
  };

  const columns: ProColumns<SupplierPublic>[] = [
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '名称 / 编码 / 邮箱 / 电话',
      },
    },
    {
      title: '供应商编码',
      dataIndex: 'code',
      search: false,
      width: 120,
    },
    {
      title: '供应商名称',
      dataIndex: 'name',
      search: false,
      ellipsis: true,
      render: (dom, entity) => (
        <Button type="link" onClick={() => openView(entity.id)}>
          {dom}
        </Button>
      ),
    },
    {
      title: '联系电话',
      dataIndex: 'phone',
      search: false,
      width: 140,
    },
    {
      title: '邮件地址',
      dataIndex: 'email',
      search: false,
      ellipsis: true,
    },
    ...(access.canPlatform
      ? [
          {
            title: '维护管理员',
            dataIndex: 'created_by_name',
            search: false,
            width: 140,
            ellipsis: true,
            render: (_: unknown, record: SupplierPublic) =>
              record.created_by_name || '-',
          } as ProColumns<SupplierPublic>,
        ]
      : []),
    {
      title: '创建时间',
      dataIndex: 'created_at',
      search: false,
      width: 180,
      render: (_, record) => formatDateTime(record.created_at),
    },
    {
      title: '操作',
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 200,
      render: (_, record) => [
        <Button type="link" key="detail" onClick={() => openView(record.id)}>
          {'查看'}
        </Button>,
        canUpdate ? (
          <Button type="link" key="edit" onClick={() => openEdit(record.id)}>
            {'编辑'}
          </Button>
        ) : null,
        canDelete ? (
          <Popconfirm
            key="delete"
            title={'确认删除该供应商？删除后其下属账号将一并停用。'}
            onConfirm={async () => {
              try {
                await deleteSupplier(record.id);
                message.success(
                  '删除成功',
                );
                actionRef.current?.reload();
              } catch {
                // 错误已由全局拦截器处理
              }
            }}
          >
            <Button type="link" danger>
              {'删除'}
            </Button>
          </Popconfirm>
        ) : null,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable<SupplierPublic, SupplierTableParams>
        headerTitle={'供应商列表'}
        actionRef={actionRef}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        pagination={{
          defaultPageSize: PAGE_SIZE_DEFAULT,
          pageSizeOptions: [10, 20, 50, 100],
          showSizeChanger: true,
        }}
        toolBarRender={() =>
          canCreate
            ? [
                <Button
                  type="primary"
                  key="create"
                  icon={<PlusOutlined />}
                  onClick={openCreate}
                >
                  {'新建'}
                </Button>,
              ]
            : []
        }
        request={async (params) => {
          try {
            const result = await fetchSupplierList({
              page: params.current,
              page_size: params.pageSize,
              keyword: params.keyword?.trim() || undefined,
            });
            return {
              data: result.items,
              success: true,
              total: result.total,
            };
          } catch {
            return {
              data: [],
              success: false,
              total: 0,
            };
          }
        }}
        columns={columns}
      />

      <SupplierFormDrawer
        open={drawerOpen}
        mode={drawerMode}
        supplierId={activeId}
        onClose={closeDrawer}
        onSuccess={() => actionRef.current?.reload()}
        onSwitchToEdit={
          drawerMode === 'view' && activeId && canUpdate
            ? () => setDrawerMode('edit')
            : undefined
        }
      />
    </PageContainer>
  );
};

export default SupplierList;
