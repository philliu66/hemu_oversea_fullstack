import { UploadOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { useIntl } from '@umijs/max';
import {
  App,
  Button,
  Image,
  Modal,
  Popconfirm,
  Space,
  Tag,
  Typography,
  Upload,
} from 'antd';
import React, { useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  deleteMissionFissionData,
  fetchMissionFissionDataList,
  markMissionFissionDataFinished,
} from '@/services/admin/missions';
import type { FissionStatus, MissionFissionDataPublic } from '@/types/api';
import { AddFissionDrawer } from './AddFissionDrawer';
import { ViewFissionDrawer } from './ViewFissionDrawer';

type FissionTableParams = {
  current?: number;
  pageSize?: number;
};

const FISSION_COLOR: Record<FissionStatus, string> = {
  pending: 'default',
  success: 'success',
  failed: 'error',
  marked_finished: 'warning',
};

export function FissionDataTable({
  missionId,
  editable = false,
}: {
  missionId: number;
  editable?: boolean;
}) {
  const intl = useIntl();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [viewDataId, setViewDataId] = useState<number>();

  const statusLabel = (status: FissionStatus) => {
    const id = {
      pending: 'pages.mission.fissionStatus.pending',
      success: 'pages.mission.fissionStatus.success',
      failed: 'pages.mission.fissionStatus.failed',
      marked_finished: 'pages.mission.fissionStatus.markedFinished',
    }[status];
    return intl.formatMessage({ id, defaultMessage: status });
  };

  const columns: ProColumns<MissionFissionDataPublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.product',
        defaultMessage: '商品',
      }),
      dataIndex: 'product',
      search: false,
      width: 320,
      render: (_, record) => (
        <Space align="start" size={12} style={{ maxWidth: '100%' }}>
          {record.main_image_url ? (
            <Image
              src={record.main_image_url}
              alt={record.item_name || record.item_code || undefined}
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
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {record.item_code || '-'}
            </Typography.Text>
          </div>
        </Space>
      ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.store',
        defaultMessage: '店铺',
      }),
      dataIndex: 'store_name',
      search: false,
      width: 140,
      ellipsis: true,
      render: (_, record) => record.store_name || String(record.store_id),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.fissionStatus',
        defaultMessage: '裂变状态',
      }),
      dataIndex: 'fission_status',
      search: false,
      render: (_, record) => (
        <Tag color={FISSION_COLOR[record.fission_status]}>
          {statusLabel(record.fission_status)}
        </Tag>
      ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.fissionMsg',
        defaultMessage: '裂变信息',
      }),
      dataIndex: 'fission_msg',
      search: false,
      ellipsis: true,
      render: (_, record) => record.fission_msg || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.list.field.option',
        defaultMessage: '操作',
      }),
      dataIndex: 'option',
      valueType: 'option' as const,
      search: false as const,
      width: editable ? 240 : 100,
      render: (_: unknown, record: MissionFissionDataPublic) => {
        const actions = [
          <Button
            key="view"
            type="link"
            onClick={() => {
              setViewDataId(record.id);
              setViewOpen(true);
            }}
          >
            {intl.formatMessage({
              id: 'pages.mission.action.viewChanges',
              defaultMessage: '查看变更',
            })}
          </Button>,
        ];
        if (!editable || record.fission_status === 'success') {
          return actions;
        }
        if (record.fission_status !== 'marked_finished') {
          actions.push(
            <Popconfirm
              key="finish"
              title={intl.formatMessage({
                id: 'pages.mission.fissionData.markFinishedConfirm',
                defaultMessage: '确认将这条任务数据标记结束？',
              })}
              onConfirm={async () => {
                try {
                  await markMissionFissionDataFinished({
                    id: record.id,
                    mission_id: missionId,
                  });
                  message.success(
                    intl.formatMessage({
                      id: 'pages.mission.fissionData.markFinishedSuccess',
                      defaultMessage: '已标记结束',
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
                  id: 'pages.mission.action.markFinished',
                  defaultMessage: '标记结束',
                })}
              </Button>
            </Popconfirm>,
          );
        }
        actions.push(
          <Popconfirm
            key="delete"
            title={intl.formatMessage({
              id: 'pages.mission.fissionData.deleteConfirm',
              defaultMessage: '确认删除这条任务数据？',
            })}
            onConfirm={async () => {
              try {
                await deleteMissionFissionData({
                  id: record.id,
                  mission_id: missionId,
                });
                message.success(
                  intl.formatMessage({
                    id: 'pages.mission.fissionData.deleteSuccess',
                    defaultMessage: '已删除',
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
                id: 'pages.mission.fissionData.delete',
                defaultMessage: '删除',
              })}
            </Button>
          </Popconfirm>,
        );
        return actions;
      },
    },
  ];

  return (
    <>
      <ProTable<MissionFissionDataPublic, FissionTableParams>
        actionRef={actionRef}
        rowKey="id"
        search={false}
        scroll={{ x: 1280 }}
        headerTitle={intl.formatMessage({
          id: 'pages.mission.data.section',
          defaultMessage: '任务数据',
        })}
        pagination={{
          defaultPageSize: PAGE_SIZE_DEFAULT,
          showSizeChanger: true,
        }}
        toolBarRender={
          editable
            ? () => [
                <Button key="add" onClick={() => setAddOpen(true)}>
                  {intl.formatMessage({
                    id: 'pages.mission.action.add',
                    defaultMessage: '手动添加',
                  })}
                </Button>,
                <Button key="import" onClick={() => setImportOpen(true)}>
                  {intl.formatMessage({
                    id: 'pages.mission.action.import',
                    defaultMessage: '批量导入',
                  })}
                </Button>,
              ]
            : false
        }
        request={async (params) => {
          const result = await fetchMissionFissionDataList({
            mission_id: missionId,
            page: params.current,
            page_size: params.pageSize,
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
      <AddFissionDrawer
        open={addOpen}
        missionId={missionId}
        onClose={() => setAddOpen(false)}
        onAdded={() => {
          setAddOpen(false);
          actionRef.current?.reload();
        }}
      />
      <Modal
        title={intl.formatMessage({
          id: 'pages.mission.action.import',
          defaultMessage: '批量导入',
        })}
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        okButtonProps={{ disabled: true }}
      >
        <p>
          {intl.formatMessage({
            id: 'pages.mission.import.placeholder',
            defaultMessage:
              '后续将上传指定格式的 Excel，解析后批量加入任务数据。',
          })}
        </p>
        <Upload disabled>
          <Button disabled icon={<UploadOutlined />}>
            Excel
          </Button>
        </Upload>
      </Modal>
    </>
  );
}
