import { App, Button, Drawer, Form, Input, Space } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';
import PermissionCodePicker from '@/components/PermissionCodePicker';
import {
  createRole,
  fetchRolePermissionTree,
  type PermissionTreeNode,
  type RolePublic,
  updateRole,
} from '@/services/admin/rbac';

type FormValues = {
  name: string;
  remark?: string;
  permission_codes: string[];
};

export function RoleFormDrawer({
  open,
  editing,
  portalRole,
  onClose,
  onSuccess,
}: {
  open: boolean;
  editing: RolePublic | null;
  portalRole?: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [permTree, setPermTree] = useState<PermissionTreeNode[]>([]);

  const isEdit = !!editing;

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    fetchRolePermissionTree(portalRole)
      .then((nodes) => {
        if (!cancelled) {
          setPermTree(nodes);
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
        name: editing.name,
        remark: editing.remark || undefined,
        permission_codes: editing.permission_codes ?? [],
      });
    } else {
      form.setFieldsValue({
        name: undefined,
        remark: undefined,
        permission_codes: [],
      });
    }
  }, [editing, form, open]);

  const title = useMemo(
    () => (isEdit ? '编辑角色' : '新建角色'),
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
        await updateRole(portalRole, {
          id: editing.id,
          name: values.name.trim(),
          remark: values.remark?.trim(),
          permission_codes: values.permission_codes ?? [],
        });
        message.success('保存成功');
      } else {
        await createRole(portalRole, {
          name: values.name.trim(),
          remark: values.remark?.trim(),
          permission_codes: values.permission_codes ?? [],
        });
        message.success('创建成功');
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
      width={720}
      destroyOnHidden
      maskClosable={false}
      onClose={handleClose}
      styles={{ body: { paddingBottom: 80 } }}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={handleClose}>{'取消'}</Button>
          <Button type="primary" loading={submitting} onClick={handleSubmit}>
            {'确定'}
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Form.Item
          name="name"
          label={'角色名称'}
          rules={[
            {
              required: true,
              message: '请输入角色名称',
            },
          ]}
        >
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="remark" label={'备注'}>
          <Input.TextArea maxLength={255} rows={2} />
        </Form.Item>
        <Form.Item
          name="permission_codes"
          label={'权限'}
          rules={[
            {
              required: true,
              type: 'array',
              min: 1,
              message: '请选择权限',
            },
          ]}
        >
          <PermissionCodePicker
            tree={permTree}
            maxHeight="calc(100vh - 360px)"
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
