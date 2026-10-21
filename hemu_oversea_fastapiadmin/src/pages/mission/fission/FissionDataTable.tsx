import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import {
  App,
  Button,
  Image,
  Popconfirm,
  Space,
  Tag,
  Typography,
} from 'antd';
import React, { useCallback, useRef, useState } from 'react';
import type { Key } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  deleteMissionFissionData,
  fetchMissionFissionDataList,
  markMissionFissionDataFinished,
} from '@/services/admin/missions';
import { publishDhProduct } from '@/services/admin/products';
import type { FissionStatus, MissionFissionDataPublic } from '@/types/api';
import { AddFissionDrawer } from './AddFissionDrawer';
import { EditFissionDrawer } from './EditFissionDrawer';
import { ViewFissionDrawer } from './ViewFissionDrawer';

type FissionTableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
  fission_status?: string;
};

const FISSION_COLOR: Record<FissionStatus, string> = {
  pending: 'default',
  success: 'success',
  failed: 'error',
  marked_finished: 'warning',
};

const FISSION_STATUS_LABEL: Record<FissionStatus, string> = {
  pending: '待裂变',
  success: '成功',
  failed: '失败',
  marked_finished: '标记结束',
};

export function FissionDataTable({
  missionId,
  supplierId,
  editable = false,
}: {
  missionId: number;
  supplierId?: number;
  editable?: boolean;
}) {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [viewDataId, setViewDataId] = useState<number>();
  const [editOpen, setEditOpen] = useState(false);
  const [editDataId, setEditDataId] = useState<number>();
  const [publishingId, setPublishingId] = useState<number>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  const clearSelection = useCallback(() => {
    setSelectedRowKeys([]);
  }, []);

  const resolveSelectedIds = useCallback(() => {
    return selectedRowKeys
      .map((k) => Number(k))
      .filter((n) => Number.isFinite(n) && n > 0);
  }, [selectedRowKeys]);

  const handleBatchMarkFinished = useCallback(async () => {
    const ids = resolveSelectedIds();
    if (!ids.length) {
      message.warning('请先选择任务数据');
      return;
    }
    setBatchLoading(true);
    try {
      await markMissionFissionDataFinished({
        id: ids,
        mission_id: missionId,
      });
      message.success(`已标记结束 ${ids.length} 条`);
      clearSelection();
      actionRef.current?.reload();
    } catch {
      // 错误已由全局拦截器处理
    } finally {
      setBatchLoading(false);
    }
  }, [clearSelection, message, missionId, resolveSelectedIds]);

  const handleBatchDelete = useCallback(async () => {
    const ids = resolveSelectedIds();
    if (!ids.length) {
      message.warning('请先选择任务数据');
      return;
    }
    setBatchLoading(true);
    try {
      await deleteMissionFissionData({
        id: ids,
        mission_id: missionId,
      });
      message.success(`已删除 ${ids.length} 条`);
      clearSelection();
      actionRef.current?.reload();
    } catch {
      // 错误已由全局拦截器处理
    } finally {
      setBatchLoading(false);
    }
  }, [clearSelection, message, missionId, resolveSelectedIds]);

  const statusLabel = (status: FissionStatus) =>
    FISSION_STATUS_LABEL[status] ?? status;

  const copyCode = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      message.success('已复制');
    } catch {
      message.error('复制失败');
    }
  };

  const renderCodeTag = (
    value: string | null | undefined,
    color: string,
  ) => {
    const text = (value || '').trim() || '-';
    const canCopy = text !== '-';
    return (
      <Tag
        color={color}
        style={{ cursor: canCopy ? 'pointer' : 'default', marginInlineEnd: 0 }}
        onClick={() => {
          if (canCopy) {
            void copyCode(text);
          }
        }}
      >
        {text}
      </Tag>
    );
  };

  const columns: ProColumns<MissionFissionDataPublic>[] = [
    {
      title: '搜索内容',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '商品标题 / 原商品编码 / 新商品编码',
        allowClear: true,
      },
    },
    {
      title: '商品',
      dataIndex: 'product',
      search: false,
      width: 360,
      render: (_, record) => (
        <Space align="start" size={12} style={{ maxWidth: '100%' }}>
          {record.main_image_url ? (
            <Image
              src={record.main_image_url}
              alt={
                record.item_name ||
                record.seed_item_code ||
                record.item_code ||
                undefined
              }
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
            <Typography.Paragraph
              ellipsis={{ rows: 2, tooltip: record.item_name || undefined }}
              style={{ marginBottom: 4 }}
            >
              {record.item_name || '-'}
            </Typography.Paragraph>
            <Space size={4} wrap>
              {renderCodeTag(record.seed_item_code, 'default')}
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {'->'}
              </Typography.Text>
              {renderCodeTag(record.item_code, 'success')}
            </Space>
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
      render: (_, record) => record.store_name || String(record.store_id),
    },
    {
      title: '裂变状态',
      dataIndex: 'fission_status',
      valueType: 'select',
      initialValue: 'all',
      fieldProps: {
        allowClear: false,
      },
      valueEnum: {
        all: { text: '全部' },
        pending: { text: '待裂变' },
        success: { text: '成功' },
        failed: { text: '失败' },
        marked_finished: { text: '标记结束' },
      },
      width: 200,
      render: (_, record) => {
        const msg = (record.fission_msg || '').trim();
        return (
          <div style={{ minWidth: 0, maxWidth: 200 }}>
            <Tag color={FISSION_COLOR[record.fission_status]}>
              {statusLabel(record.fission_status)}
            </Tag>
            {msg ? (
              <Typography.Paragraph
                type="secondary"
                ellipsis={{ rows: 1, tooltip: msg }}
                style={{
                  marginBottom: 0,
                  marginTop: 4,
                  fontSize: 12,
                  lineHeight: 1.4,
                }}
              >
                {msg}
              </Typography.Paragraph>
            ) : null}
          </div>
        );
      },
    },
    {
      title: '操作',
      dataIndex: 'option',
      valueType: 'option' as const,
      search: false as const,
      width: editable ? 220 : 200,
      render: (_: unknown, record: MissionFissionDataPublic) => {
        const actions = [
          <Button
            key="view"
            color="default"
            variant="filled"
            size="small"
            shape="round"
            onClick={() => {
              setViewDataId(record.id);
              setViewOpen(true);
            }}
          >
            {'查看变更'}
          </Button>,
        ];
        // 裂变成功：仅保留查看变更
        if (record.fission_status !== 'success') {
          // 详情页与设置任务数据页均支持单个裂变
          actions.push(
            <Popconfirm
              key="fission"
              title={'确认对该任务数据进行单个裂变发布？'}
              onConfirm={async () => {
                setPublishingId(record.id);
                try {
                  const result = await publishDhProduct({
                    type: 'addfission',
                    mission_data_fission_id: record.id,
                    supplier_id: supplierId,
                  });
                  message.success(
                    result.item_code
                      ? `裂变成功：${result.item_code}`
                      : '裂变成功',
                  );
                  actionRef.current?.reload();
                } catch {
                  // 失败时后端可能已写回状态，仍刷新列表
                  actionRef.current?.reload();
                } finally {
                  setPublishingId(undefined);
                }
              }}
            >
              <Button
                type="primary"
                size="small"
                shape="round"
                loading={publishingId === record.id}
              >
                {'单个裂变'}
              </Button>
            </Popconfirm>,
          );
          if (editable) {
            actions.push(
              <Button
                key="edit"
                type="dashed"
                size="small"
                shape="round"
                onClick={() => {
                  setEditDataId(record.id);
                  setEditOpen(true);
                }}
              >
                {'编辑'}
              </Button>,
            );
            if (record.fission_status !== 'marked_finished') {
              actions.push(
                <Popconfirm
                  key="finish"
                  title={'确认将这条任务数据标记结束？'}
                  onConfirm={async () => {
                    try {
                      await markMissionFissionDataFinished({
                        id: record.id,
                        mission_id: missionId,
                      });
                      message.success('已标记结束');
                      actionRef.current?.reload();
                    } catch {
                      // 错误已由全局拦截器处理
                    }
                  }}
                >
                  <Button type="primary" danger size="small" shape="round">
                    {'标记结束'}
                  </Button>
                </Popconfirm>,
              );
            }
            actions.push(
              <Popconfirm
                key="delete"
                title={'确认删除这条任务数据？'}
                onConfirm={async () => {
                  try {
                    await deleteMissionFissionData({
                      id: record.id,
                      mission_id: missionId,
                    });
                    message.success('已删除');
                    actionRef.current?.reload();
                  } catch {
                    // 错误已由全局拦截器处理
                  }
                }}
              >
                <Button danger size="small" shape="round">
                  {'删除'}
                </Button>
              </Popconfirm>,
            );
          }
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
            }}
          >
            {actions}
          </div>
        );
      },
    },
  ];

  return (
    <>
      <ProTable<MissionFissionDataPublic, FissionTableParams>
        actionRef={actionRef}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 1140 }}
        headerTitle={'任务数据'}
        pagination={{
          defaultPageSize: PAGE_SIZE_DEFAULT,
          showSizeChanger: true,
        }}
        rowSelection={
          editable
            ? {
                selectedRowKeys,
                onChange: setSelectedRowKeys,
                getCheckboxProps: (record) => ({
                  // 裂变成功不可删/不可标记结束
                  disabled: record.fission_status === 'success',
                }),
              }
            : undefined
        }
        tableAlertOptionRender={() =>
          editable ? (
            <Space size={16}>
              <Popconfirm
                title={`确认将选中的 ${selectedRowKeys.length} 条标记结束？`}
                disabled={!selectedRowKeys.length || batchLoading}
                onConfirm={() => void handleBatchMarkFinished()}
              >
                <a>批量标记结束</a>
              </Popconfirm>
              <Popconfirm
                title={`确认删除选中的 ${selectedRowKeys.length} 条？`}
                disabled={!selectedRowKeys.length || batchLoading}
                onConfirm={() => void handleBatchDelete()}
              >
                <a>批量删除</a>
              </Popconfirm>
              <a onClick={clearSelection}>取消选择</a>
            </Space>
          ) : (
            false
          )
        }
        toolBarRender={
          editable
            ? () => [
                <Button key="add" onClick={() => setAddOpen(true)}>
                  {'手动添加'}
                </Button>,
                // 暂时屏蔽批量导入
              ]
            : false
        }
        request={async (params) => {
          const keyword = params.keyword?.trim() || undefined;
          const statusRaw = (params.fission_status || '').trim();
          const fission_status =
            !statusRaw || statusRaw === 'all' ? undefined : statusRaw;
          const result = await fetchMissionFissionDataList({
            mission_id: missionId,
            page: params.current,
            page_size: params.pageSize,
            keyword,
            fission_status,
          });
          return {
            data: result.items,
            success: true,
            total: result.total,
          };
        }}
        columns={columns}
      />
      <ViewFissionDrawer
        open={viewOpen}
        missionId={missionId}
        dataId={viewDataId}
        onClose={() => setViewOpen(false)}
      />
      <EditFissionDrawer
        open={editOpen}
        missionId={missionId}
        dataId={editDataId}
        onClose={() => {
          setEditOpen(false);
          setEditDataId(undefined);
        }}
        onSaved={() => {
          setEditOpen(false);
          setEditDataId(undefined);
          actionRef.current?.reload();
        }}
      />
      <AddFissionDrawer
        open={addOpen}
        missionId={missionId}
        supplierId={supplierId}
        onClose={() => setAddOpen(false)}
        onAdded={() => {
          setAddOpen(false);
          actionRef.current?.reload();
        }}
      />
    </>
  );
}
