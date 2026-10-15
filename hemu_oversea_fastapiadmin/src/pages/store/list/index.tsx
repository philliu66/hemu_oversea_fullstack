import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import { App, Button, Popconfirm, Space, Tag } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import SupplierSelectField from '@/components/SupplierSelectField';
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
import {
  needsSupplierSelection,
  resolveRequestSupplierId,
} from '@/utils/portalScope';
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
  supplier_id?: number;
};

function isOauthStatus(value: number): value is StoreOauthStatusValue {
  return (
    value === STORE_OAUTH_STATUS.UNAUTHORIZED ||
    value === STORE_OAUTH_STATUS.AUTHORIZED ||
    value === STORE_OAUTH_STATUS.EXPIRED
  );
}

const StoreList: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const actionRef = useRef<ActionType | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<StoreDrawerMode>('create');
  const [activeId, setActiveId] = useState<number>();
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();

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
            '授权成功',
        );
        return;
      }

      if (status === 'fail') {
        message.error(
          msg ||
            '授权失败',
        );
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [message]);

  const openCreate = () => {
    if (needsSupplierSelection(currentUser, selectedSupplierId)) {
      message.warning('请先选择供应商');
      return;
    }
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
        text: STORE_TYPE_LABEL[type],
      },
    ]),
  );

  const renderOauthTag = (oauthStatus: number) => {
    if (!isOauthStatus(oauthStatus)) {
      return null;
    }
    return (
      <Tag color={STORE_OAUTH_STATUS_COLOR[oauthStatus]}>
        {STORE_OAUTH_STATUS_LABEL[oauthStatus]}
      </Tag>
    );
  };

  const handleAuthorize = async (storeId: number) => {
    try {
      const data = await fetchStoreAuthorizeUrl(storeId);
      if (!data.authorize_url) {
        message.error(
          '未获取到授权链接',
        );
        return;
      }
      const popup = openAuthorizeWindow(data.authorize_url);
      if (!popup) {
        message.warning(
          '浏览器拦截了弹窗，请允许后重试',
        );
      }
    } catch {
      // 错误已由全局拦截器处理
    }
  };

  const columns: ProColumns<StorePublic>[] = [
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
          } as ProColumns<StorePublic>,
          {
            title: '供应商',
            dataIndex: 'supplier_name',
            search: false,
            width: 160,
            ellipsis: true,
            render: (_, record) => record.supplier_name || '-',
          } as ProColumns<StorePublic>,
        ]
      : []),
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '名称 / 标识 / 账号',
      },
    },
    {
      title: '店铺类型',
      dataIndex: 'store_type',
      valueType: 'select',
      valueEnum: storeTypeValueEnum,
      width: 120,
    },
    {
      title: '店铺名称',
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
      title: '店铺标识',
      dataIndex: 'identifier',
      search: false,
      ellipsis: true,
    },
    {
      title: '基础折扣率',
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
      title: '创建人',
      dataIndex: 'created_by',
      search: false,
      hideInTable: true,
      width: 120,
      ellipsis: true,
      render: (_, record) => record.created_by || '-',
    },
    {
      title: '更新时间',
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
            {'授权到期'}
            ：{formatDateTime(record.refresh_token_expires_at)}
          </div>
        </div>
      ),
    },
    {
      title: '操作',
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 180,
      render: (_, record) => (
        <Space size={0} wrap>
          <Button type="link" size="small" onClick={() => openView(record.id)}>
            {'查看'}
          </Button>
          <Button type="link" size="small" onClick={() => openEdit(record.id)}>
            {'编辑'}
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => void handleAuthorize(record.id)}
          >
            {'授权'}
          </Button>
          <Popconfirm
            title={'确认删除该店铺？'}
            onConfirm={async () => {
              try {
                await deleteStore(record.id);
                message.success(
                  '删除成功',
                );
                actionRef.current?.reload();
              } catch {
                // 错误已由全局拦截器处理
              }
            }}
          >
            <Button type="link" size="small" danger>
              {'删除'}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<StorePublic, StoreTableParams>
        headerTitle={'店铺列表'}
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
            {'新建'}
          </Button>,
        ]}
        request={async (params) => {
          const supplierId = resolveRequestSupplierId(
            currentUser,
            params.supplier_id ?? selectedSupplierId,
          );
          if (needsSupplierSelection(currentUser, supplierId)) {
            return { data: [], success: true, total: 0 };
          }
          try {
            const result = await fetchStoreList({
              page: params.current,
              page_size: params.pageSize,
              keyword: params.keyword?.trim() || undefined,
              store_type:
                typeof params.store_type === 'string' && params.store_type
                  ? (params.store_type as StoreType)
                  : undefined,
              supplier_id: supplierId,
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
        supplierId={resolveRequestSupplierId(currentUser, selectedSupplierId)}
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
