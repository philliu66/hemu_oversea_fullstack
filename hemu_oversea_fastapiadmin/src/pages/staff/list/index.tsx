import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import { App, Button, Popconfirm, Tag, Typography } from 'antd';
import React, { useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  deleteStaff,
  fetchStaffList,
  updateStaffStatus,
} from '@/services/admin/supplierStaff';
import type { UserPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { StaffFormDrawer } from './StaffFormDrawer';

type StaffTableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
};

const StaffListPage: React.FC = () => {
  const access = useAccess();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const portalRole = initialState?.currentUser?.role;
  const actionRef = useRef<ActionType | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<UserPublic | null>(null);

  const canCreate = access.can('personnel.staff.create');
  const canUpdate = access.can('personnel.staff.update');
  const canDelete = access.can('personnel.staff.delete');

  const openCreate = () => {
    setEditing(null);
    setDrawerOpen(true);
  };

  const openEdit = (record: UserPublic) => {
    setEditing(record);
    setDrawerOpen(true);
  };

  const columns: ProColumns<UserPublic>[] = [
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '账号 / 昵称 / 邮箱 / 手机号',
      },
    },
    {
      title: '账号',
      dataIndex: 'username',
      search: false,
      ellipsis: true,
      width: 120,
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      search: false,
      ellipsis: true,
      width: 100,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      search: false,
      ellipsis: true,
      width: 180,
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      search: false,
      width: 120,
      ellipsis: true,
      render: (_, record) => record.phone || '-',
    },
    {
      title: '角色',
      dataIndex: 'roles',
      search: false,
      width: 140,
      // 自定义 render 时列级 ellipsis 不生效，需自行截断
      render: (_, record) => {
        const text = record.roles?.length
          ? record.roles.map((r) => r.name).join('、')
          : '-';
        return (
          <Typography.Text ellipsis={{ tooltip: text }} style={{ maxWidth: '100%' }}>
            {text}
          </Typography.Text>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      search: false,
      width: 80,
      render: (_, record) =>
        record.is_active ? (
          <Tag color="success">
            {'启用'}
          </Tag>
        ) : (
          <Tag>
            {'停用'}
          </Tag>
        ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      search: false,
      width: 170,
      render: (_, record) => formatDateTime(record.created_at),
    },
    {
      title: '操作',
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 200,
      hideInTable: !canUpdate && !canDelete,
      render: (_, record) => {
        const actions: React.ReactNode[] = [];
        if (canUpdate) {
          actions.push(
            <Button
              key="edit"
              type="dashed"
              size="small"
              shape="round"
              onClick={() => openEdit(record)}
            >
              {'编辑'}
            </Button>,
          );
          actions.push(
            <Popconfirm
              key="status"
              title={
                record.is_active ? '确认停用该员工？' : '确认启用该员工？'
              }
              onConfirm={async () => {
                try {
                  await updateStaffStatus(portalRole, {
                    id: record.id,
                    is_active: !record.is_active,
                  });
                  message.success('状态已更新');
                  actionRef.current?.reload();
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button
                color="default"
                variant="filled"
                size="small"
                shape="round"
              >
                {record.is_active ? '停用' : '启用'}
              </Button>
            </Popconfirm>,
          );
        }
        if (canDelete) {
          actions.push(
            <Popconfirm
              key="delete"
              title={'确认删除该员工？删除后不可登录。'}
              onConfirm={async () => {
                try {
                  await deleteStaff(portalRole, record.id);
                  message.success('删除成功');
                  actionRef.current?.reload();
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button type="primary" danger size="small" shape="round">
                {'删除'}
              </Button>
            </Popconfirm>,
          );
        }
        // 一行最多 2 个按钮，超出自动换行
        return (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, max-content)',
              gap: 8,
              justifyContent: 'start',
              alignItems: 'center',
              maxWidth: '100%',
            }}
          >
            {actions}
          </div>
        );
      },
    },
  ];

  return (
    <PageContainer>
      <ProTable<UserPublic, StaffTableParams>
        headerTitle={'员工管理'}
        actionRef={actionRef}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 1100 }}
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
                  {'新建员工'}
                </Button>,
              ]
            : []
        }
        request={async (params) => {
          try {
            const result = await fetchStaffList(portalRole, {
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

      <StaffFormDrawer
        open={drawerOpen}
        editing={editing}
        portalRole={portalRole}
        onClose={() => {
          setDrawerOpen(false);
          setEditing(null);
        }}
        onSuccess={() => actionRef.current?.reload()}
      />
    </PageContainer>
  );
};

export default StaffListPage;
