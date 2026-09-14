import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useIntl } from '@umijs/max';
import { App, Button, Form, Input, Modal, Popconfirm, Space, Tag } from 'antd';
import React, { useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  createSupplierStaff,
  deleteSupplierStaff,
  fetchSupplierStaffList,
  updateSupplierStaff,
  updateSupplierStaffStatus,
} from '@/services/admin/supplierStaff';
import type { UserPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';

type StaffTableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
};

type StaffFormValues = {
  username: string;
  nickname?: string;
  email: string;
  phone?: string;
  password?: string;
  confirmPassword?: string;
};

function confirmPasswordMatch(
  getFieldValue: (name: string) => unknown,
  value?: string,
) {
  if (!value || getFieldValue('password') === value) {
    return Promise.resolve();
  }
  return Promise.reject(new Error('两次输入的密码不一致'));
}

const StaffListPage: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType | null>(null);
  const [form] = Form.useForm<StaffFormValues>();
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editing, setEditing] = useState<UserPublic | null>(null);

  const isEdit = !!editing;

  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (record: UserPublic) => {
    setEditing(record);
    form.setFieldsValue({
      username: record.username,
      nickname: record.nickname,
      email: record.email,
      phone: record.phone || undefined,
      password: undefined,
      confirmPassword: undefined,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (isEdit && editing) {
        const phone = values.phone?.trim();
        await updateSupplierStaff({
          id: editing.id,
          nickname: values.nickname?.trim() || undefined,
          email: values.email.trim(),
          phone: phone || undefined,
          password: values.password || undefined,
        });
        message.success(
          intl.formatMessage({
            id: 'pages.staff.edit.success',
            defaultMessage: '保存成功',
          }),
        );
      } else {
        await createSupplierStaff({
          username: values.username.trim(),
          password: values.password || '',
          nickname: values.nickname?.trim() || undefined,
          email: values.email.trim(),
          phone: values.phone?.trim() || undefined,
        });
        message.success(
          intl.formatMessage({
            id: 'pages.staff.create.success',
            defaultMessage: '创建成功',
          }),
        );
      }
      closeModal();
      actionRef.current?.reload();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
      // 业务错误已由全局拦截器处理
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ProColumns<UserPublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.keyword',
        defaultMessage: '关键词',
      }),
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: intl.formatMessage({
          id: 'pages.staff.field.keywordPlaceholder',
          defaultMessage: '账号 / 昵称 / 邮箱 / 手机号',
        }),
      },
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.username',
        defaultMessage: '账号',
      }),
      dataIndex: 'username',
      search: false,
      width: 140,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.nickname',
        defaultMessage: '昵称',
      }),
      dataIndex: 'nickname',
      search: false,
      width: 120,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.email',
        defaultMessage: '邮箱',
      }),
      dataIndex: 'email',
      search: false,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.phone',
        defaultMessage: '手机号',
      }),
      dataIndex: 'phone',
      search: false,
      width: 140,
      render: (_, record) => record.phone || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.status',
        defaultMessage: '状态',
      }),
      dataIndex: 'is_active',
      search: false,
      width: 100,
      render: (_, record) =>
        record.is_active ? (
          <Tag color="success">
            {intl.formatMessage({
              id: 'pages.account.status.active',
              defaultMessage: '启用',
            })}
          </Tag>
        ) : (
          <Tag>
            {intl.formatMessage({
              id: 'pages.account.status.inactive',
              defaultMessage: '停用',
            })}
          </Tag>
        ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.createdAt',
        defaultMessage: '创建时间',
      }),
      dataIndex: 'created_at',
      search: false,
      width: 180,
      render: (_, record) => formatDateTime(record.created_at),
    },
    {
      title: intl.formatMessage({
        id: 'pages.staff.field.option',
        defaultMessage: '操作',
      }),
      dataIndex: 'option',
      valueType: 'option',
      search: false,
      width: 220,
      render: (_, record) => (
        <Space size={0} wrap>
          <Button type="link" onClick={() => openEdit(record)}>
            {intl.formatMessage({
              id: 'pages.staff.action.edit',
              defaultMessage: '编辑',
            })}
          </Button>
          <Popconfirm
            title={intl.formatMessage({
              id: record.is_active
                ? 'pages.staff.disable.confirm'
                : 'pages.staff.enable.confirm',
              defaultMessage: record.is_active
                ? '确认停用该员工？'
                : '确认启用该员工？',
            })}
            onConfirm={async () => {
              try {
                await updateSupplierStaffStatus({
                  id: record.id,
                  is_active: !record.is_active,
                });
                message.success(
                  intl.formatMessage({
                    id: 'pages.staff.status.success',
                    defaultMessage: '状态已更新',
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
                id: record.is_active
                  ? 'pages.staff.action.disable'
                  : 'pages.staff.action.enable',
                defaultMessage: record.is_active ? '停用' : '启用',
              })}
            </Button>
          </Popconfirm>
          <Popconfirm
            title={intl.formatMessage({
              id: 'pages.staff.delete.confirm',
              defaultMessage: '确认删除该员工？删除后不可登录。',
            })}
            onConfirm={async () => {
              try {
                await deleteSupplierStaff(record.id);
                message.success(
                  intl.formatMessage({
                    id: 'pages.staff.delete.success',
                    defaultMessage: '删除成功',
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
                id: 'pages.staff.action.delete',
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
      <ProTable<UserPublic, StaffTableParams>
        headerTitle={intl.formatMessage({
          id: 'pages.staff.list.title',
          defaultMessage: '员工管理',
        })}
        actionRef={actionRef}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
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
              id: 'pages.staff.action.create',
              defaultMessage: '新建员工',
            })}
          </Button>,
        ]}
        request={async (params) => {
          try {
            const result = await fetchSupplierStaffList({
              page: params.current,
              page_size: params.pageSize,
              keyword: params.keyword?.trim() || undefined,
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

      <Modal
        title={intl.formatMessage({
          id: isEdit ? 'pages.staff.modal.edit' : 'pages.staff.modal.create',
          defaultMessage: isEdit ? '编辑员工' : '新建员工',
        })}
        open={modalOpen}
        onCancel={closeModal}
        onOk={() => void handleSubmit()}
        confirmLoading={submitting}
        destroyOnHidden
        width={480}
      >
        <Form<StaffFormValues>
          form={form}
          layout="vertical"
          autoComplete="off"
          className="mt-4"
        >
          <Form.Item
            name="username"
            label={intl.formatMessage({
              id: 'pages.staff.field.username',
              defaultMessage: '账号',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.staff.field.usernameRequired',
                  defaultMessage: '请输入账号',
                }),
              },
              {
                min: 3,
                message: intl.formatMessage({
                  id: 'pages.staff.field.usernameMin',
                  defaultMessage: '账号至少 3 位',
                }),
              },
            ]}
          >
            <Input
              maxLength={50}
              disabled={isEdit}
              placeholder={intl.formatMessage({
                id: 'pages.staff.field.usernamePlaceholder',
                defaultMessage: '请输入员工账号',
              })}
            />
          </Form.Item>
          <Form.Item
            name="nickname"
            label={intl.formatMessage({
              id: 'pages.staff.field.nickname',
              defaultMessage: '昵称',
            })}
          >
            <Input
              maxLength={50}
              placeholder={intl.formatMessage({
                id: 'pages.staff.field.nicknamePlaceholder',
                defaultMessage: '请输入昵称',
              })}
            />
          </Form.Item>
          <Form.Item
            name="email"
            label={intl.formatMessage({
              id: 'pages.staff.field.email',
              defaultMessage: '邮箱',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.staff.field.emailRequired',
                  defaultMessage: '请输入邮箱',
                }),
              },
              {
                type: 'email',
                message: intl.formatMessage({
                  id: 'pages.staff.field.emailInvalid',
                  defaultMessage: '请输入正确的邮箱',
                }),
              },
            ]}
          >
            <Input
              maxLength={255}
              placeholder={intl.formatMessage({
                id: 'pages.staff.field.emailPlaceholder',
                defaultMessage: '请输入邮箱',
              })}
            />
          </Form.Item>
          <Form.Item
            name="phone"
            label={intl.formatMessage({
              id: 'pages.staff.field.phone',
              defaultMessage: '手机号',
            })}
            rules={[
              {
                validator: async (_, value?: string) => {
                  const phone = value?.trim();
                  if (!phone || phone.length >= 5) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error(
                      intl.formatMessage({
                        id: 'pages.staff.field.phoneMin',
                        defaultMessage: '手机号至少 5 位',
                      }),
                    ),
                  );
                },
              },
            ]}
          >
            <Input
              maxLength={20}
              placeholder={intl.formatMessage({
                id: 'pages.staff.field.phonePlaceholder',
                defaultMessage: '请输入手机号',
              })}
            />
          </Form.Item>
          <Form.Item
            name="password"
            label={intl.formatMessage({
              id: isEdit
                ? 'pages.staff.field.newPassword'
                : 'pages.staff.field.password',
              defaultMessage: isEdit ? '新密码（可选）' : '密码',
            })}
            rules={
              isEdit
                ? [
                    {
                      min: 6,
                      message: intl.formatMessage({
                        id: 'pages.staff.field.passwordMin',
                        defaultMessage: '密码至少 6 位',
                      }),
                    },
                  ]
                : [
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'pages.staff.field.passwordRequired',
                        defaultMessage: '请输入密码',
                      }),
                    },
                    {
                      min: 6,
                      message: intl.formatMessage({
                        id: 'pages.staff.field.passwordMin',
                        defaultMessage: '密码至少 6 位',
                      }),
                    },
                  ]
            }
          >
            <Input.Password
              autoComplete="new-password"
              placeholder={intl.formatMessage({
                id: isEdit
                  ? 'pages.staff.field.newPasswordPlaceholder'
                  : 'pages.staff.field.passwordPlaceholder',
                defaultMessage: isEdit ? '不修改请留空' : '请输入密码',
              })}
            />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label={intl.formatMessage({
              id: 'pages.staff.field.confirmPassword',
              defaultMessage: '确认密码',
            })}
            dependencies={['password']}
            rules={[
              ({ getFieldValue }) => ({
                validator: async (_, value?: string) => {
                  const password = getFieldValue('password') as
                    | string
                    | undefined;
                  if (!isEdit || password) {
                    if (!value) {
                      return Promise.reject(
                        new Error(
                          intl.formatMessage({
                            id: 'pages.staff.field.confirmPasswordRequired',
                            defaultMessage: '请再次输入密码',
                          }),
                        ),
                      );
                    }
                  }
                  return confirmPasswordMatch(getFieldValue, value);
                },
              }),
            ]}
          >
            <Input.Password
              autoComplete="new-password"
              placeholder={intl.formatMessage({
                id: 'pages.staff.field.confirmPasswordPlaceholder',
                defaultMessage: '请再次输入密码',
              })}
            />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default StaffListPage;
