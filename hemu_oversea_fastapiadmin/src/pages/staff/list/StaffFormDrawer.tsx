import { App, Button, Drawer, Form, Input, Select, Space } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';
import { fetchRoleOptions } from '@/services/admin/rbac';
import { createStaff, updateStaff } from '@/services/admin/supplierStaff';
import type { UserPublic } from '@/types/api';

type FormValues = {
  username: string;
  nickname?: string;
  email: string;
  phone?: string;
  password?: string;
  confirmPassword?: string;
  role_ids: number[];
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

export function StaffFormDrawer({
  open,
  editing,
  portalRole,
  onClose,
  onSuccess,
}: {
  open: boolean;
  editing: UserPublic | null;
  portalRole?: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [roleOptions, setRoleOptions] = useState<
    { id: number; name: string }[]
  >([]);

  const isEdit = !!editing;

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    fetchRoleOptions(portalRole)
      .then((options) => {
        if (!cancelled) {
          setRoleOptions(options);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [open, portalRole]);

  useEffect(() => {
    if (!open) {
      form.resetFields();
      return;
    }
    if (editing) {
      form.setFieldsValue({
        username: editing.username,
        nickname: editing.nickname,
        email: editing.email,
        phone: editing.phone || undefined,
        password: undefined,
        confirmPassword: undefined,
        role_ids: editing.roles?.map((r) => r.id) ?? [],
      });
    } else {
      form.setFieldsValue({
        username: undefined,
        nickname: undefined,
        email: undefined,
        phone: undefined,
        password: undefined,
        confirmPassword: undefined,
        role_ids: [],
      });
    }
  }, [editing, form, open]);

  const title = useMemo(
    () =>
      isEdit
        ? '编辑员工'
        : '新建员工',
    [isEdit],
  );

  const handleClose = () => {
    form.resetFields();
    onClose();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateStaff(portalRole, {
          id: editing.id,
          nickname: values.nickname?.trim() || undefined,
          email: values.email.trim(),
          phone: values.phone?.trim() || undefined,
          password: values.password || undefined,
          role_ids: values.role_ids ?? [],
        });
        message.success(
          '保存成功',
        );
      } else {
        await createStaff(portalRole, {
          username: values.username.trim(),
          password: values.password || '',
          nickname: values.nickname?.trim() || undefined,
          email: values.email.trim(),
          phone: values.phone?.trim() || undefined,
          role_ids: values.role_ids ?? [],
        });
        message.success(
          '创建成功',
        );
      }
      onSuccess();
      handleClose();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Drawer
      title={title}
      open={open}
      width={480}
      destroyOnHidden
      onClose={handleClose}
      styles={{ body: { paddingBottom: 80 } }}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={handleClose}>
            {'取消'}
          </Button>
          <Button type="primary" loading={submitting} onClick={handleSubmit}>
            {'确定'}
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" autoComplete="off" preserve={false}>
        <Form.Item
          name="username"
          label={'账号'}
          rules={[
            {
              required: true,
              message: '请输入账号',
            },
            {
              min: 3,
              message: '账号至少 3 位',
            },
          ]}
        >
          <Input
            maxLength={50}
            disabled={isEdit}
            placeholder={'请输入员工账号'}
          />
        </Form.Item>
        <Form.Item
          name="nickname"
          label={'昵称'}
        >
          <Input
            maxLength={50}
            placeholder={'请输入昵称'}
          />
        </Form.Item>
        <Form.Item
          name="email"
          label={'邮箱'}
          rules={[
            {
              required: true,
              message: '请输入邮箱',
            },
            {
              type: 'email',
              message: '请输入正确的邮箱',
            },
          ]}
        >
          <Input
            maxLength={255}
            placeholder={'请输入邮箱'}
          />
        </Form.Item>
        <Form.Item
          name="phone"
          label={'手机号'}
          rules={[
            {
              validator: async (_, value?: string) => {
                const phone = value?.trim();
                if (!phone || phone.length >= 5) {
                  return Promise.resolve();
                }
                return Promise.reject(
                  new Error(
                    '手机号至少 5 位',
                  ),
                );
              },
            },
          ]}
        >
          <Input
            maxLength={20}
            placeholder={'请输入手机号'}
          />
        </Form.Item>
        <Form.Item
          name="role_ids"
          label={'角色'}
          rules={[
            {
              required: true,
              type: 'array',
              min: 1,
              message: '请选择角色',
            },
          ]}
        >
          <Select
            mode="multiple"
            allowClear
            optionFilterProp="label"
            placeholder={'请选择业务角色'}
            options={roleOptions.map((r) => ({
              label: r.name,
              value: r.id,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="password"
          label={isEdit ? '新密码（可选）' : '密码'}
          rules={
            isEdit
              ? [
                  {
                    min: 6,
                    message: '密码至少 6 位',
                  },
                ]
              : [
                  {
                    required: true,
                    message: '请输入密码',
                  },
                  {
                    min: 6,
                    message: '密码至少 6 位',
                  },
                ]
          }
        >
          <Input.Password
            autoComplete="new-password"
            placeholder={isEdit ? '不修改请留空' : '请输入密码'}
          />
        </Form.Item>
        <Form.Item
          name="confirmPassword"
          label={'确认密码'}
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
                        '请再次输入密码',
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
            placeholder={'请再次输入密码'}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
