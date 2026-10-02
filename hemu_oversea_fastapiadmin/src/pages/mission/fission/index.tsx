import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useAccess } from '@umijs/max';
import { App, Button, Form, Input, Modal, Popconfirm, Select } from 'antd';
import React, { useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  createMission,
  fetchMissionList,
  markMissionFinished,
} from '@/services/admin/missions';
import { fetchSupplierUserOptions } from '@/services/admin/users';
import type { MissionPublic, SupplierUserOption } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { MissionStatusTag } from './MissionInfo';
import {
  missionFissionDataPath,
  missionFissionDetailPath,
  personLabel,
} from './utils';

type MissionTableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
};

type CreateFormValues = {
  title: string;
  description?: string;
  worker_id: number;
};

const MissionFissionList: React.FC = () => {
  const access = useAccess();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType | null>(null);
  const [form] = Form.useForm<CreateFormValues>();
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [workers, setWorkers] = useState<SupplierUserOption[]>([]);

  const openCreate = async () => {
    form.resetFields();
    setModalOpen(true);
    try {
      const options = await fetchSupplierUserOptions();
      setWorkers(options);
    } catch {
      setWorkers([]);
    }
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await createMission({
        title: values.title.trim(),
        description: values.description?.trim() || undefined,
        worker_id: values.worker_id,
      });
      message.success(
        '创建成功',
      );
      setModalOpen(false);
      actionRef.current?.reload();
    } catch {
      // 校验失败或请求错误已提示
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ProColumns<MissionPublic>[] = [
    {
      title: '任务标题',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '请输入任务标题',
      },
    },
    {
      title: '任务标题',
      dataIndex: 'title',
      search: false,
      ellipsis: true,
    },
    {
      title: '任务状态',
      dataIndex: 'status',
      search: false,
      render: (_, record) => <MissionStatusTag status={record.status} />,
    },
    {
      title: '创建人',
      dataIndex: 'creator_nickname',
      search: false,
      render: (_, record) =>
        personLabel(record.creator_nickname, record.creator_username),
    },
    {
      title: '任务人员',
      dataIndex: 'worker_nickname',
      search: false,
      render: (_, record) =>
        personLabel(record.worker_nickname, record.worker_username),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      search: false,
      render: (_, record) => formatDateTime(record.created_at),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 280,
      render: (_, record) => {
        const canMark =
          access.can('mission.fission.finish') &&
          (record.status === 'pending' || record.status === 'running');
        return [
          access.can('mission.fission.data') ? (
            <Button
              type="link"
              key="data"
              onClick={() => history.push(missionFissionDataPath(record.id))}
            >
              {'设置任务数据'}
            </Button>
          ) : null,
          <Button
            type="link"
            key="detail"
            onClick={() => history.push(missionFissionDetailPath(record.id))}
          >
            {'详情'}
          </Button>,
          canMark ? (
            <Popconfirm
              key="finish"
              title={'确认将该任务标记结束？'}
              onConfirm={async () => {
                try {
                  await markMissionFinished(record.id);
                  message.success(
                    '已标记结束',
                  );
                  actionRef.current?.reload();
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button type="link">
                {'标记结束'}
              </Button>
            </Popconfirm>
          ) : null,
        ];
      },
    },
  ];

  return (
    <PageContainer>
      <ProTable<MissionPublic, MissionTableParams>
        headerTitle={'商品裂变'}
        actionRef={actionRef}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        pagination={{
          defaultPageSize: PAGE_SIZE_DEFAULT,
          pageSizeOptions: [10, 20, 50, 100],
          showSizeChanger: true,
        }}
        toolBarRender={() =>
          access.can('mission.fission.create')
            ? [
                <Button
                  type="primary"
                  key="create"
                  icon={<PlusOutlined />}
                  onClick={openCreate}
                >
                  {'新建任务'}
                </Button>,
              ]
            : []
        }
        request={async (params) => {
          const result = await fetchMissionList({
            page: params.current,
            page_size: params.pageSize,
            keyword: params.keyword?.trim() || undefined,
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
        title={'新建任务'}
        open={modalOpen}
        confirmLoading={submitting}
        onCancel={() => setModalOpen(false)}
        onOk={handleCreate}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="title"
            label={'任务标题'}
            rules={[
              {
                required: true,
                whitespace: true,
                message: '请输入任务标题',
              },
              { max: 100 },
            ]}
          >
            <Input
              placeholder={'请输入任务标题'}
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={'任务描述'}
          >
            <Input.TextArea
              rows={3}
              placeholder={'请输入任务描述'}
            />
          </Form.Item>
          <Form.Item
            name="worker_id"
            label={'任务人员'}
            rules={[
              {
                required: true,
                message: '请选择任务人员',
              },
            ]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder={'请选择任务人员'}
              options={workers.map((user) => ({
                value: user.id,
                label: personLabel(user.nickname, user.username),
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default MissionFissionList;
