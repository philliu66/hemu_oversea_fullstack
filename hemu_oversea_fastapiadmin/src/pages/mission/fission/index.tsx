import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useAccess, useIntl } from '@umijs/max';
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
  const intl = useIntl();
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
        intl.formatMessage({
          id: 'pages.mission.create.success',
          defaultMessage: '创建成功',
        }),
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
      title: intl.formatMessage({
        id: 'pages.mission.field.keyword',
        defaultMessage: '任务标题',
      }),
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: intl.formatMessage({
          id: 'pages.mission.field.keywordPlaceholder',
          defaultMessage: '请输入任务标题',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.title',
        defaultMessage: '任务标题',
      }),
      dataIndex: 'title',
      search: false,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.status',
        defaultMessage: '任务状态',
      }),
      dataIndex: 'status',
      search: false,
      render: (_, record) => <MissionStatusTag status={record.status} />,
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.creator',
        defaultMessage: '创建人',
      }),
      dataIndex: 'creator_nickname',
      search: false,
      render: (_, record) =>
        personLabel(record.creator_nickname, record.creator_username),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.worker',
        defaultMessage: '任务人员',
      }),
      dataIndex: 'worker_nickname',
      search: false,
      render: (_, record) =>
        personLabel(record.worker_nickname, record.worker_username),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.createdAt',
        defaultMessage: '创建时间',
      }),
      dataIndex: 'created_at',
      search: false,
      render: (_, record) => formatDateTime(record.created_at),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.option',
        defaultMessage: '操作',
      }),
      valueType: 'option',
      width: 280,
      render: (_, record) => {
        const canMark =
          access.canSupplierAdmin &&
          (record.status === 'pending' || record.status === 'running');
        return [
          access.canSupplierAdmin ? (
            <Button
              type="link"
              key="data"
              onClick={() => history.push(missionFissionDataPath(record.id))}
            >
              {intl.formatMessage({
                id: 'pages.mission.action.data',
                defaultMessage: '设置任务数据',
              })}
            </Button>
          ) : null,
          <Button
            type="link"
            key="detail"
            onClick={() => history.push(missionFissionDetailPath(record.id))}
          >
            {intl.formatMessage({
              id: 'pages.mission.action.detail',
              defaultMessage: '详情',
            })}
          </Button>,
          canMark ? (
            <Popconfirm
              key="finish"
              title={intl.formatMessage({
                id: 'pages.mission.markFinished.confirm',
                defaultMessage: '确认将该任务标记结束？',
              })}
              onConfirm={async () => {
                try {
                  await markMissionFinished(record.id);
                  message.success(
                    intl.formatMessage({
                      id: 'pages.mission.markFinished.success',
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
            </Popconfirm>
          ) : null,
        ];
      },
    },
  ];

  return (
    <PageContainer>
      <ProTable<MissionPublic, MissionTableParams>
        headerTitle={intl.formatMessage({
          id: 'pages.mission.list.title',
          defaultMessage: '商品裂变',
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
          access.canSupplierAdmin
            ? [
                <Button
                  type="primary"
                  key="create"
                  icon={<PlusOutlined />}
                  onClick={openCreate}
                >
                  {intl.formatMessage({
                    id: 'pages.mission.action.create',
                    defaultMessage: '新建任务',
                  })}
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
        title={intl.formatMessage({
          id: 'pages.mission.create.title',
          defaultMessage: '新建任务',
        })}
        open={modalOpen}
        confirmLoading={submitting}
        onCancel={() => setModalOpen(false)}
        onOk={handleCreate}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="title"
            label={intl.formatMessage({
              id: 'pages.mission.field.title',
              defaultMessage: '任务标题',
            })}
            rules={[
              {
                required: true,
                whitespace: true,
                message: intl.formatMessage({
                  id: 'pages.mission.field.titleRequired',
                  defaultMessage: '请输入任务标题',
                }),
              },
              { max: 100 },
            ]}
          >
            <Input
              placeholder={intl.formatMessage({
                id: 'pages.mission.field.titlePlaceholder',
                defaultMessage: '请输入任务标题',
              })}
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={intl.formatMessage({
              id: 'pages.mission.field.description',
              defaultMessage: '任务描述',
            })}
          >
            <Input.TextArea
              rows={3}
              placeholder={intl.formatMessage({
                id: 'pages.mission.field.descriptionPlaceholder',
                defaultMessage: '请输入任务描述',
              })}
            />
          </Form.Item>
          <Form.Item
            name="worker_id"
            label={intl.formatMessage({
              id: 'pages.mission.field.worker',
              defaultMessage: '任务人员',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.mission.field.workerRequired',
                  defaultMessage: '请选择任务人员',
                }),
              },
            ]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder={intl.formatMessage({
                id: 'pages.mission.field.workerPlaceholder',
                defaultMessage: '请选择任务人员',
              })}
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
