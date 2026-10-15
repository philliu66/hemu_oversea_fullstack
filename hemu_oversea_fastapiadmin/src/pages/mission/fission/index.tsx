import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useAccess, useModel } from '@umijs/max';
import { App, Button, Form, Input, Modal, Popconfirm, Select } from 'antd';
import React, { useRef, useState } from 'react';
import { buildPlatformSupplierSearchColumn } from '@/components/SupplierSelectField';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  createMission,
  fetchMissionList,
  markMissionFinished,
  updateMission,
} from '@/services/admin/missions';
import { fetchSupplierUserOptions } from '@/services/admin/users';
import type { MissionPublic, SupplierUserOption } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import {
  needsSupplierSelection,
  resolveRequestSupplierId,
} from '@/utils/portalScope';
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
  supplier_id?: number;
};

type MissionFormValues = {
  title: string;
  description?: string;
  worker_id: number;
};

const MissionFissionList: React.FC = () => {
  const access = useAccess();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const actionRef = useRef<ActionType | null>(null);
  const [form] = Form.useForm<MissionFormValues>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingMission, setEditingMission] = useState<MissionPublic | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);
  const [workers, setWorkers] = useState<SupplierUserOption[]>([]);
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();
  const supplierId = resolveRequestSupplierId(currentUser, selectedSupplierId);

  const loadWorkers = async (scopedSupplierId?: number) => {
    if (needsSupplierSelection(currentUser, scopedSupplierId)) {
      setWorkers([]);
      return;
    }
    try {
      const options = await fetchSupplierUserOptions({
        supplier_id: scopedSupplierId,
      });
      setWorkers(options);
    } catch {
      setWorkers([]);
    }
  };

  const openCreate = async () => {
    if (needsSupplierSelection(currentUser, supplierId)) {
      message.warning('请先选择供应商');
      return;
    }
    setEditingMission(null);
    form.resetFields();
    setModalOpen(true);
    await loadWorkers(supplierId);
  };

  const openEdit = async (record: MissionPublic) => {
    const scopedSupplierId = resolveRequestSupplierId(
      currentUser,
      record.supplier_id ?? selectedSupplierId,
    );
    setEditingMission(record);
    form.setFieldsValue({
      title: record.title,
      description: record.description || undefined,
      worker_id: record.worker_id,
    });
    setModalOpen(true);
    await loadWorkers(scopedSupplierId);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingMission) {
        await updateMission({
          id: editingMission.id,
          title: values.title.trim(),
          description: values.description?.trim() || undefined,
          worker_id: values.worker_id,
          supplier_id: resolveRequestSupplierId(
            currentUser,
            editingMission.supplier_id ?? selectedSupplierId,
          ),
        });
        message.success('更新成功');
      } else {
        if (needsSupplierSelection(currentUser, supplierId)) {
          message.warning('请先选择供应商');
          return;
        }
        await createMission({
          title: values.title.trim(),
          description: values.description?.trim() || undefined,
          worker_id: values.worker_id,
          supplier_id: supplierId,
        });
        message.success('创建成功');
      }
      setModalOpen(false);
      setEditingMission(null);
      actionRef.current?.reload();
    } catch {
      // 校验失败或请求错误已提示
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ProColumns<MissionPublic>[] = [
    ...(access.canPlatform
      ? [
          buildPlatformSupplierSearchColumn<MissionPublic>({
            onChange: (v) => {
              setSelectedSupplierId(v);
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
          } as ProColumns<MissionPublic>,
        ]
      : []),
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
      width: 220,
      render: (_, record) => {
        const canEdit =
          access.canWriteSupplierData &&
          access.can('mission.fission.create') &&
          (record.status === 'pending' || record.status === 'running');
        const canMark =
          access.canWriteSupplierData &&
          access.can('mission.fission.finish') &&
          (record.status === 'pending' || record.status === 'running');
        const actions: React.ReactNode[] = [];
        if (access.can('mission.fission.data') || access.canPlatform) {
          actions.push(
            <Button
              key="data"
              type="primary"
              size="small"
              shape="round"
              onClick={() => history.push(missionFissionDataPath(record.id))}
            >
              {access.canWriteSupplierData ? '设置任务数据' : '查看任务数据'}
            </Button>,
          );
        }
        if (canEdit) {
          actions.push(
            <Button
              key="edit"
              type="dashed"
              size="small"
              shape="round"
              onClick={() => openEdit(record)}
            >
              {'编辑'}
            </Button>,
          );
        }
        actions.push(
          <Button
            key="detail"
            color="default"
            variant="filled"
            size="small"
            shape="round"
            onClick={() => history.push(missionFissionDetailPath(record.id))}
          >
            {'详情'}
          </Button>,
        );
        if (canMark) {
          actions.push(
            <Popconfirm
              key="finish"
              title={'确认将该任务标记结束？'}
              onConfirm={async () => {
                try {
                  await markMissionFinished(record.id);
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
          access.canWriteSupplierData && access.can('mission.fission.create')
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
          const scopedSupplierId = resolveRequestSupplierId(
            currentUser,
            params.supplier_id ?? selectedSupplierId,
          );
          if (needsSupplierSelection(currentUser, scopedSupplierId)) {
            return { data: [], success: true, total: 0 };
          }
          const result = await fetchMissionList({
            page: params.current,
            page_size: params.pageSize,
            keyword: params.keyword?.trim() || undefined,
            supplier_id: scopedSupplierId,
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
        title={editingMission ? '编辑任务' : '新建任务'}
        open={modalOpen}
        confirmLoading={submitting}
        onCancel={() => {
          setModalOpen(false);
          setEditingMission(null);
        }}
        onOk={handleSubmit}
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
            <Input placeholder={'请输入任务标题'} />
          </Form.Item>
          <Form.Item name="description" label={'任务描述'}>
            <Input.TextArea rows={3} placeholder={'请输入任务描述'} />
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
