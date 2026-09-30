import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useIntl } from '@umijs/max';
import { App, Button, Popconfirm, Space, Tag } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  STORE_OAUTH_RESULT_MESSAGE_TYPE,
  STORE_OAUTH_STATUS,
  STORE_OAUTH_STATUS_COLOR,
  STORE_OAUTH_STATUS_LABEL,
  STORE_TYPE_LABEL,
  STORE_TYPES,
  type StoreOauthStatusValue,
} from '@/constants/store';
import {
  deleteStore,
  fetchStoreAuthorizeUrl,
  fetchStoreList,
} from '@/services/admin/stores';
import type { StorePublic, StoreType } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { openAuthorizeWindow } from '../openAuthorizeWindow';
import {
  StoreFormDrawer,
  type StoreDrawerMode,
} from './StoreFormDrawer';

type StoreTableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
  store_type?: StoreType | string;
};

function isOauthStatus(value: number): value is StoreOauthStatusValue {
  return (
    value === STORE_OAUTH_STATUS.UNAUTHORIZED ||
    value === STORE_OAUTH_STATUS.AUTHORIZED ||
    value === STORE_OAUTH_STATUS.EXPIRED
  );
}

const StoreList: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<StoreDrawerMode>('create');
  const [activeId, setActiveId] = useState<number>();

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) {
        return;
      }
      const data = event.data;
      if (
        !data ||
        typeof data !== 'object' ||
        data.type !== STORE_OAUTH_RESULT_MESSAGE_TYPE
      ) {
        return;
      }

      const status = String(data.status || '');
      const msg = String(data.msg || '').trim();

      if (status === 'success') {
        actionRef.current?.reload();
        message.success(
          msg ||
            intl.formatMessage({
              id: 'pages.store.oauth.success',
              defaultMessage: '授权成功',
            }),
        );
        return;
      }

      if (status === 'fail') {
        message.error(
          msg ||
            intl.formatMessage({
              id: 'pages.store.oauth.fail',
              defaultMessage: '授权失败',
            }),
        );
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [intl, message]);

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

  const storeTypeValueEnum = Object.fromEntries(
    STORE_TYPES.map((type) => [
      type,
      {
        text: intl.formatMessage({
          id: `pages.store.type.${type}`,
          defaultMessage: STORE_TYPE_LABEL[type],
        }),
      },
    ]),
  );

  const renderOauthTag = (oauthStatus: number) => {
    if (!isOauthStatus(oauthStatus)) {
      return null;
    }
    return (
      <Tag color={STORE_OAUTH_STATUS_COLOR[oauthStatus]}>
        {intl.formatMessage({
          id: `pages.store.oauthStatus.${oauthStatus}`,
          defaultMessage: STORE_OAUTH_STATUS_LABEL[oauthStatus],
        })}
      </Tag>
    );
  };

  const handleAuthorize = async (storeId: number) => {
    try {
      const data = await fetchStoreAuthorizeUrl(storeId);
      if (!data.authorize_url) {
        message.error(
          intl.formatMessage({
            id: 'pages.store.oauth.urlEmpty',
            defaultMessage: '未获取到授权链接',
          }),
        );
        return;
      }
      const popup = openAuthorizeWindow(data.authorize_url);
      if (!popup) {
        message.warning(
          intl.formatMessage({
            id: 'pages.store.oauth.popupBlocked',
            defaultMessage: '浏览器拦截了弹窗，请允许后重试',
          }),
        );
      }
    } catch {
      // 错误已由全局拦截器处理
    }
  };

  const columns: ProColumns<StorePublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.store.field.keyword',
        defaultMessage: '关键词',
      }),
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: intl.formatMessage({
          id: 'pages.store.field.keywordPlaceholder',
          defaultMessage: '名称 / 标识 / 账号',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.store.field.storeType',
        defaultMessage: '店铺类型',
      }),
      dataIndex: 'store_type',
      valueType: 'select',
      valueEnum: storeTypeValueEnum,
      width: 120,
    },
    {
      title: intl.formatMessage({
        id: 'pages.store.field.name',
        defaultMessage: '店铺名称',
      }),
      dataIndex: 'name',
      search: false,
      ellipsis: true,
      render: (_, entity) => (
        <Space size={8} wrap>
          <Button
            type="link"
            style={{ paddingInline: 0 }}
            onClick={() => openView(entity.id)}
          >
            {entity.name}
          </Button>
          {renderOauthTag(entity.oauth_status)}
        </Space>
      ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.store.field.identifier',
        defaultMessage: '店铺标识',
      }),
      dataIndex: 'identifier',
      search: false,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.store.field.baseDiscount',
        defaultMessage: '基础折扣率',
      }),
      dataIndex: 'base_discount',
      search: false,
      width: 120,
      render: (_, record) => {
        const value = Number(record.base_discount);
        if (!Number.isFinite(value)) {
          return '-';
        }
        return value.toFixed(2);
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.store.field.createdBy',
        defaultMessage: '创建人',
      }),
      dataIndex: 'created_by',
      search: false,
      hideInTable: true,
      width: 120,
      ellipsis: true,
      render: (_, record) => record.created_by || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.store.field.updatedAt',
        defaultMessage: '更新时间',
      }),
      dataIndex: 'updated_at',
      search: false,
      width: 180,
      render: (_, record) => (
        <div>
          <div>{formatDateTime(record.updated_at)}</div>
          <div
            style={{
              marginTop: 2,
              fontSize: 12,
              lineHeight: 1.4,
              color: 'rgba(0, 0, 0, 0.45)',
            }}
          >
            {intl.formatMessage({
              id: 'pages.store.field.refreshTokenExpiresAt',
              defaultMessage: '授权到期',
            })}
            ：{formatDateTime(record.refresh_token_expires_at)}
          </div>
        </div>
      ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.store.field.option',
        defaultMessage: '操作',
      }),
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 180,
      render: (_, record) => (
        <Space size={0} wrap>
          <Button type="link" size="small" onClick={() => openView(record.id)}>
            {intl.formatMessage({
              id: 'pages.store.action.detail',
              defaultMessage: '查看',
            })}
          </Button>
          <Button type="link" size="small" onClick={() => openEdit(record.id)}>
            {intl.formatMessage({
              id: 'pages.store.action.edit',
              defaultMessage: '编辑',
            })}
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => void handleAuthorize(record.id)}
          >
            {intl.formatMessage({
              id: 'pages.store.action.authorize',
              defaultMessage: '授权',
            })}
          </Button>
          <Popconfirm
            title={intl.formatMessage({
              id: 'pages.store.delete.confirm',
              defaultMessage: '确认删除该店铺？',
            })}
            onConfirm={async () => {
              try {
                await deleteStore(record.id);
                message.success(
                  intl.formatMessage({
                    id: 'pages.store.delete.success',
                    defaultMessage: '删除成功',
                  }),
                );
                actionRef.current?.reload();
              } catch {
                // 错误已由全局拦截器处理
              }
            }}
          >
            <Button type="link" size="small" danger>
              {intl.formatMessage({
                id: 'pages.store.action.delete',
                defaultMessage: '删除',
              })}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<StorePublic, StoreTableParams>
        headerTitle={intl.formatMessage({
          id: 'pages.store.list.title',
          defaultMessage: '店铺列表',
        })}
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
        toolBarRender={() => [
          <Button
            type="primary"
            key="create"
            icon={<PlusOutlined />}
            onClick={openCreate}
          >
            {intl.formatMessage({
              id: 'pages.store.action.create',
              defaultMessage: '新建',
            })}
          </Button>,
        ]}
        request={async (params) => {
          try {
            const result = await fetchStoreList({
              page: params.current,
              page_size: params.pageSize,
              keyword: params.keyword?.trim() || undefined,
              store_type:
                typeof params.store_type === 'string' && params.store_type
                  ? (params.store_type as StoreType)
                  : undefined,
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

      <StoreFormDrawer
        open={drawerOpen}
        mode={drawerMode}
        storeId={activeId}
        onClose={closeDrawer}
        onSuccess={() => actionRef.current?.reload()}
        onSwitchToEdit={
          drawerMode === 'view' && activeId
            ? () => setDrawerMode('edit')
            : undefined
        }
      />
    </PageContainer>
  );
};

export default StoreList;
