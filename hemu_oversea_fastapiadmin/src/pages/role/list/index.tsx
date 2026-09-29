import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useIntl, useModel } from '@umijs/max';
import { App, Button, Popconfirm } from 'antd';
import React, { useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  deleteRole,
  listRoles,
  type RolePublic,
} from '@/services/admin/rbac';
import { formatDateTime } from '@/utils/datetime';
import { RoleFormDrawer } from './RoleFormDrawer';

type TableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
};

const RoleListPage: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const portalRole = initialState?.currentUser?.role;
  const actionRef = useRef<ActionType | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<RolePublic | null>(null);

  const openCreate = () => {
    setEditing(null);
    setDrawerOpen(true);
  };

  const openEdit = (record: RolePublic) => {
    setEditing(record);
    setDrawerOpen(true);
  };

  const columns: ProColumns<RolePublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.role.field.name',
        defaultMessage: '角色名称',
      }),
      dataIndex: 'name',
      hideInSearch: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.role.field.keyword',
        defaultMessage: '关键词',
      }),
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: intl.formatMessage({
          id: 'pages.role.field.name',
          defaultMessage: '角色名称',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.role.field.remark',
        defaultMessage: '备注',
      }),
      dataIndex: 'remark',
      hideInSearch: true,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.role.field.permCount',
        defaultMessage: '权限数',
      }),
      hideInSearch: true,
      width: 100,
      render: (_, r) => r.permission_codes?.length ?? 0,
    },
    {
      title: intl.formatMessage({
        id: 'pages.role.field.createdAt',
        defaultMessage: '创建时间',
      }),
      dataIndex: 'created_at',
      hideInSearch: true,
      width: 180,
      render: (_, r) => formatDateTime(r.created_at),
    },
    {
      title: intl.formatMessage({
        id: 'pages.role.field.option',
        defaultMessage: '操作',
      }),
      valueType: 'option',
      width: 160,
      render: (_, record) => [
        <a key="edit" onClick={() => openEdit(record)}>
          {intl.formatMessage({
            id: 'pages.role.action.edit',
            defaultMessage: '编辑',
          })}
        </a>,
        <Popconfirm
          key="delete"
          title={intl.formatMessage({
            id: 'pages.role.delete.confirm',
            defaultMessage: '确认删除该角色？',
          })}
          onConfirm={async () => {
            await deleteRole(portalRole, record.id);
            message.success(
              intl.formatMessage({
                id: 'pages.role.delete.success',
                defaultMessage: '删除成功',
              }),
            );
            actionRef.current?.reload();
          }}
        >
          <a>
            {intl.formatMessage({
              id: 'pages.role.action.delete',
              defaultMessage: '删除',
            })}
          </a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable<RolePublic, TableParams>
        headerTitle={intl.formatMessage({
          id: 'pages.role.list.title',
          defaultMessage: '角色管理',
        })}
        actionRef={actionRef}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button
            type="primary"
            key="create"
            icon={<PlusOutlined />}
            onClick={openCreate}
          >
            {intl.formatMessage({
              id: 'pages.role.action.create',
              defaultMessage: '新建角色',
            })}
          </Button>,
        ]}
        request={async (params) => {
          const data = await listRoles(portalRole, {
            keyword: params.keyword,
            page: params.current ?? 1,
            page_size: params.pageSize ?? PAGE_SIZE_DEFAULT,
          });
          return {
            data: data.items,
            total: data.total,
            success: true,
          };
        }}
        columns={columns}
        pagination={{
          defaultPageSize: PAGE_SIZE_DEFAULT,
          showSizeChanger: true,
        }}
      />

      <RoleFormDrawer
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

export default RoleListPage;
