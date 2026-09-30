import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, useIntl, useModel } from '@umijs/max';
import { App, Button, Popconfirm, Space, Tag } from 'antd';
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
  const intl = useIntl();
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
      title: intl.formatMessage({
        id: 'pages.staff.field.keyword',
        defaultMessage: '关键词',
      }),
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: intl.formatMessage({
          id: 'pages.staff.field.keywordPlaceholder',
          defaultMessage: '账号 / 昵称 / 邮箱 / 手机号',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.username',
        defaultMessage: '账号',
      }),
      dataIndex: 'username',
      search: false,
      width: 140,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.nickname',
        defaultMessage: '昵称',
      }),
      dataIndex: 'nickname',
      search: false,
      width: 120,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.email',
        defaultMessage: '邮箱',
      }),
      dataIndex: 'email',
      search: false,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.phone',
        defaultMessage: '手机号',
      }),
      dataIndex: 'phone',
      search: false,
      width: 140,
      render: (_, record) => record.phone || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.roles',
        defaultMessage: '角色',
      }),
      dataIndex: 'roles',
      search: false,
      width: 160,
      ellipsis: true,
      render: (_, record) =>
        record.roles?.length
          ? record.roles.map((r) => r.name).join('、')
          : '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.status',
        defaultMessage: '状态',
      }),
      dataIndex: 'is_active',
      search: false,
      width: 100,
      render: (_, record) =>
        record.is_active ? (
          <Tag color="success">
            {intl.formatMessage({
              id: 'pages.account.status.active',
              defaultMessage: '启用',
            })}
          </Tag>
        ) : (
          <Tag>
            {intl.formatMessage({
              id: 'pages.account.status.inactive',
              defaultMessage: '停用',
            })}
          </Tag>
        ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.createdAt',
        defaultMessage: '创建时间',
      }),
      dataIndex: 'created_at',
      search: false,
      width: 180,
      render: (_, record) => formatDateTime(record.created_at),
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.option',
        defaultMessage: '操作',
      }),
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 220,
      hideInTable: !canUpdate && !canDelete,
      render: (_, record) => (
        <Space size={0} wrap>
          {canUpdate ? (
            <Button type="link" onClick={() => openEdit(record)}>
              {intl.formatMessage({
                id: 'pages.staff.action.edit',
                defaultMessage: '编辑',
              })}
            </Button>
          ) : null}
          {canUpdate ? (
            <Popconfirm
              title={intl.formatMessage({
                id: record.is_active
                  ? 'pages.staff.disable.confirm'
                  : 'pages.staff.enable.confirm',
                defaultMessage: record.is_active
                  ? '确认停用该员工？'
                  : '确认启用该员工？',
              })}
              onConfirm={async () => {
                try {
                  await updateStaffStatus(portalRole, {
                    id: record.id,
                    is_active: !record.is_active,
                  });
                  message.success(
                    intl.formatMessage({
                      id: 'pages.staff.status.success',
                      defaultMessage: '状态已更新',
                    }),
                  );
                  actionRef.current?.reload();
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button type="link">
                {intl.formatMessage({
                  id: record.is_active
                    ? 'pages.staff.action.disable'
                    : 'pages.staff.action.enable',
                  defaultMessage: record.is_active ? '停用' : '启用',
                })}
              </Button>
            </Popconfirm>
          ) : null}
          {canDelete ? (
            <Popconfirm
              title={intl.formatMessage({
                id: 'pages.staff.delete.confirm',
                defaultMessage: '确认删除该员工？删除后不可登录。',
              })}
              onConfirm={async () => {
                try {
                  await deleteStaff(portalRole, record.id);
                  message.success(
                    intl.formatMessage({
                      id: 'pages.staff.delete.success',
                      defaultMessage: '删除成功',
                    }),
                  );
                  actionRef.current?.reload();
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button type="link" danger>
                {intl.formatMessage({
                  id: 'pages.staff.action.delete',
                  defaultMessage: '删除',
                })}
              </Button>
            </Popconfirm>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<UserPublic, StaffTableParams>
        headerTitle={intl.formatMessage({
          id: 'pages.staff.list.title',
          defaultMessage: '员工管理',
        })}
        actionRef={actionRef}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
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
                  {intl.formatMessage({
                    id: 'pages.staff.action.create',
                    defaultMessage: '新建员工',
                  })}
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
