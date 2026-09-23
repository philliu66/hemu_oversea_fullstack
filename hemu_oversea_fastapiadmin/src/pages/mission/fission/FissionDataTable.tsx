import { UploadOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { useIntl } from '@umijs/max';
import { Button, Modal, Tag, Upload } from 'antd';
import React, { useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import { fetchMissionFissionDataList } from '@/services/admin/missions';
import type { FissionStatus, MissionFissionDataPublic } from '@/types/api';

type FissionTableParams = {
  current?: number;
  pageSize?: number;
};

const FISSION_COLOR: Record<FissionStatus, string> = {
  pending: 'default',
  success: 'success',
  failed: 'error',
};

export function FissionDataTable({
  missionId,
  editable = false,
}: {
  missionId: number;
  editable?: boolean;
}) {
  const intl = useIntl();
  const actionRef = useRef<ActionType | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  const statusLabel = (status: FissionStatus) => {
    const id = {
      pending: 'pages.mission.fissionStatus.pending',
      success: 'pages.mission.fissionStatus.success',
      failed: 'pages.mission.fissionStatus.failed',
    }[status];
    return intl.formatMessage({ id, defaultMessage: status });
  };

  const columns: ProColumns<MissionFissionDataPublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.seedProductId',
        defaultMessage: '种子商品',
      }),
      dataIndex: 'seed_product_id',
      search: false,
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.storeId',
        defaultMessage: '店铺',
      }),
      dataIndex: 'store_id',
      search: false,
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.itemCode',
        defaultMessage: '商品编码',
      }),
      dataIndex: 'item_code',
      search: false,
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.siteId',
        defaultMessage: '站点',
      }),
      dataIndex: 'site_id',
      search: false,
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
  ];

  const placeholderColumns: ProColumns<{ id: number }>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.itemCode',
        defaultMessage: '商品编码',
      }),
      dataIndex: 'item_code',
      hideInTable: true,
      fieldProps: { disabled: true },
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.itemCode',
        defaultMessage: '商品编码',
      }),
      dataIndex: 'item_code',
      search: false,
    },
  ];

  return (
    <>
      <ProTable<MissionFissionDataPublic, FissionTableParams>
        actionRef={actionRef}
        rowKey="id"
        search={false}
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
      <Modal
        title={intl.formatMessage({
          id: 'pages.mission.action.add',
          defaultMessage: '手动添加',
        })}
        open={addOpen}
        onCancel={() => setAddOpen(false)}
        okButtonProps={{ disabled: true }}
        width={860}
      >
        <p>
          {intl.formatMessage({
            id: 'pages.mission.add.placeholder',
            defaultMessage: '后续将从种子商品中筛选并加入任务，当前仅占位。',
          })}
        </p>
        <ProTable<{ id: number }>
          rowKey="id"
          search={{
            labelWidth: 'auto',
            optionRender: () => [
              <Button key="reset" disabled>
                {intl.formatMessage({
                  id: 'pages.mission.action.searchReset',
                  defaultMessage: '重置',
                })}
              </Button>,
              <Button key="submit" type="primary" disabled>
                {intl.formatMessage({
                  id: 'pages.mission.action.search',
                  defaultMessage: '查询',
                })}
              </Button>,
            ],
          }}
          options={false}
          pagination={false}
          dataSource={[]}
          columns={placeholderColumns}
        />
      </Modal>
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
