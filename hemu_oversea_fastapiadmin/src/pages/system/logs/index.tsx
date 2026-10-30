import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import { Tabs, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import React, { useRef, useState } from 'react';
import { buildPlatformSupplierSearchColumn } from '@/components/SupplierSelectField';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  fetchLoginLogs,
  fetchOperationLogs,
  type LogListQuery,
} from '@/services/admin/logs';
import type { LoginLogPublic, OperationLogPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { isPlatformRole, isSupplierPortalRole } from '@/utils/portalScope';
import LoginActivityPanel from './LoginActivityPanel';

type LogTableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
  supplier_id?: number;
  time_from?: string;
  time_to?: string;
};

const LOGOUT_REASON_LABEL: Record<string, string> = {
  logout: '主动登出',
  logout_all: '全部登出',
  kicked: '被踢下线',
  password_change: '修改密码',
  idle: '空闲后再次操作',
};

const ACTIVITY_STATUS_LABEL: Record<LoginLogPublic['activity_status'], string> = {
  active: '活跃中',
  idle: '非活跃',
  ended: '已结束',
};

function toApiDateTime(value: unknown): string | undefined {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const parsed = dayjs(value as string);
  if (!parsed.isValid()) {
    return undefined;
  }
  return parsed.toISOString();
}

function formatStay(seconds: number): string {
  const safe = Math.max(0, seconds);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const remain = safe % 60;
  if (hours > 0) {
    return `${hours}小时${minutes}分${remain}秒`;
  }
  if (minutes > 0) {
    return `${minutes}分${remain}秒`;
  }
  return `${remain}秒`;
}

function resolveSupplierId(
  currentUser:
    | { role?: string; access?: string; supplier_id?: number | null }
    | undefined,
  selected?: number | null,
): number | undefined {
  const role = currentUser?.access || currentUser?.role;
  if (isSupplierPortalRole(role)) {
    return currentUser?.supplier_id ?? undefined;
  }
  if (isPlatformRole(role) && selected != null && selected > 0) {
    return Number(selected);
  }
  return undefined;
}

const LoginLogTable: React.FC = () => {
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const actionRef = useRef<ActionType | null>(null);
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();
  const [activityOpen, setActivityOpen] = useState(false);
  const [activityRecord, setActivityRecord] = useState<LoginLogPublic | null>(null);
  const [activityToken, setActivityToken] = useState(0);

  const columns: ProColumns<LoginLogPublic>[] = [
    ...(access.canPlatform
      ? [
          buildPlatformSupplierSearchColumn<LoginLogPublic>({
            onChange: (value) => {
              setSelectedSupplierId(value);
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
          } as ProColumns<LoginLogPublic>,
        ]
      : []),
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      order: 90,
      fieldProps: {
        placeholder: '昵称 / 邮箱 / 手机号',
      },
    },
    {
      title: '登录时间',
      dataIndex: 'login_at_range',
      valueType: 'dateTimeRange',
      hideInTable: true,
      order: 80,
      search: {
        transform: (value: [string, string]) => ({
          time_from: toApiDateTime(value?.[0]),
          time_to: toApiDateTime(value?.[1]),
        }),
      },
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      search: false,
      width: 120,
      ellipsis: true,
      render: (_, record) => {
        const label = record.nickname || record.username || '-';
        if (!record.user_id) {
          return label;
        }
        return (
          <Typography.Link
            onClick={() => {
              setActivityRecord(record);
              setActivityToken((value) => value + 1);
              setActivityOpen(true);
            }}
          >
            {label}
          </Typography.Link>
        );
      },
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      search: false,
      width: 200,
      ellipsis: true,
      render: (_, record) => record.email || '-',
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      search: false,
      width: 140,
      render: (_, record) => record.phone || '-',
    },
    {
      title: '开始时间',
      dataIndex: 'login_at',
      search: false,
      width: 180,
      render: (_, record) => formatDateTime(record.login_at),
    },
    {
      title: '最后请求',
      dataIndex: 'last_seen_at',
      search: false,
      width: 180,
      render: (_, record) => formatDateTime(record.last_seen_at),
    },
    {
      title: '状态',
      dataIndex: 'activity_status',
      search: false,
      width: 100,
      render: (_, record) => {
        const label =
          ACTIVITY_STATUS_LABEL[record.activity_status] || record.activity_status;
        if (record.activity_status === 'active') {
          return <Tag color="success">{label}</Tag>;
        }
        if (record.activity_status === 'idle') {
          return <Tag color="warning">{label}</Tag>;
        }
        return <Tag>{label}</Tag>;
      },
    },
    {
      title: '活跃截止',
      dataIndex: 'active_until',
      search: false,
      width: 180,
      render: (_, record) =>
        record.active_until ? formatDateTime(record.active_until) : '-',
    },
    {
      title: '结束时间',
      dataIndex: 'logout_at',
      search: false,
      width: 220,
      render: (_, record) => {
        if (!record.logout_at) {
          return '-';
        }
        const reason = record.logout_reason
          ? LOGOUT_REASON_LABEL[record.logout_reason] || record.logout_reason
          : '';
        return reason
          ? `${formatDateTime(record.logout_at)}（${reason}）`
          : formatDateTime(record.logout_at);
      },
    },
    {
      title: '活跃时长',
      dataIndex: 'online_seconds',
      search: false,
      width: 140,
      render: (_, record) => formatStay(record.online_seconds),
    },
  ];

  return (
    <>
    <ProTable<LoginLogPublic, LogTableParams>
      actionRef={actionRef}
      rowKey="id"
      columns={columns}
      scroll={{ x: 'max-content' }}
      search={{ labelWidth: 'auto' }}
      pagination={{
        defaultPageSize: PAGE_SIZE_DEFAULT,
        pageSizeOptions: [10, 20, 50, 100],
        showSizeChanger: true,
      }}
      request={async (params) => {
        const query: LogListQuery = {
          page: params.current,
          page_size: params.pageSize,
          keyword: params.keyword?.trim() || undefined,
          supplier_id: resolveSupplierId(
            currentUser,
            params.supplier_id ?? selectedSupplierId,
          ),
          time_from: params.time_from,
          time_to: params.time_to,
        };
        try {
          const result = await fetchLoginLogs(query);
          return {
            data: result.items,
            success: true,
            total: result.total,
          };
        } catch {
          return { data: [], success: false, total: 0 };
        }
      }}
    />
    <LoginActivityPanel
      open={activityOpen}
      seedToken={activityToken}
      record={activityRecord}
      onClose={() => setActivityOpen(false)}
    />
  </>
  );
};

const OperationLogTable: React.FC = () => {
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const actionRef = useRef<ActionType | null>(null);
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();

  const columns: ProColumns<OperationLogPublic>[] = [
    ...(access.canPlatform
      ? [
          buildPlatformSupplierSearchColumn<OperationLogPublic>({
            onChange: (value) => {
              setSelectedSupplierId(value);
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
          } as ProColumns<OperationLogPublic>,
        ]
      : []),
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      order: 90,
      fieldProps: {
        placeholder: '昵称 / 邮箱 / 手机号 / 操作名称',
      },
    },
    {
      title: '操作时间',
      dataIndex: 'created_at_range',
      valueType: 'dateTimeRange',
      hideInTable: true,
      order: 80,
      search: {
        transform: (value: [string, string]) => ({
          time_from: toApiDateTime(value?.[0]),
          time_to: toApiDateTime(value?.[1]),
        }),
      },
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      search: false,
      width: 120,
      ellipsis: true,
      render: (_, record) => record.nickname || record.actor_username || '-',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      search: false,
      width: 200,
      ellipsis: true,
      render: (_, record) => record.email || '-',
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      search: false,
      width: 140,
      render: (_, record) => record.phone || '-',
    },
    {
      title: '操作',
      dataIndex: 'summary',
      search: false,
      ellipsis: true,
      render: (_, record) => record.summary || record.action || '-',
    },
    {
      title: '操作时间',
      dataIndex: 'created_at',
      search: false,
      width: 180,
      render: (_, record) => formatDateTime(record.created_at),
    },
    {
      title: '结果',
      dataIndex: 'status',
      search: false,
      width: 90,
      render: (_, record) =>
        record.status === 'success' ? (
          <Tag color="success">成功</Tag>
        ) : (
          <Tag color="error">{record.status || '失败'}</Tag>
        ),
    },
  ];

  return (
    <ProTable<OperationLogPublic, LogTableParams>
      actionRef={actionRef}
      rowKey="id"
      columns={columns}
      search={{ labelWidth: 'auto' }}
      pagination={{
        defaultPageSize: PAGE_SIZE_DEFAULT,
        pageSizeOptions: [10, 20, 50, 100],
        showSizeChanger: true,
      }}
      request={async (params) => {
        const query: LogListQuery = {
          page: params.current,
          page_size: params.pageSize,
          keyword: params.keyword?.trim() || undefined,
          supplier_id: resolveSupplierId(
            currentUser,
            params.supplier_id ?? selectedSupplierId,
          ),
          time_from: params.time_from,
          time_to: params.time_to,
        };
        try {
          const result = await fetchOperationLogs(query);
          return {
            data: result.items,
            success: true,
            total: result.total,
          };
        } catch {
          return { data: [], success: false, total: 0 };
        }
      }}
    />
  );
};

const SystemLogsPage: React.FC = () => {
  return (
    <PageContainer>
      <Tabs
        items={[
          {
            key: 'login',
            label: '登录日志',
            children: <LoginLogTable />,
          },
          {
            key: 'operation',
            label: '操作日志',
            children: <OperationLogTable />,
          },
        ]}
      />
    </PageContainer>
  );
};

export default SystemLogsPage;
