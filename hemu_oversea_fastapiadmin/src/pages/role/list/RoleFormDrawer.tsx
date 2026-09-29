import { useIntl } from '@umijs/max';
import { App, Button, Drawer, Form, Input, Space, Tree } from 'antd';
import type { DataNode } from 'antd/es/tree';
import React, { useEffect, useMemo, useState } from 'react';
import {
  createRole,
  fetchRolePermissionTree,
  flattenPermissionTree,
  type RolePublic,
  updateRole,
} from '@/services/admin/rbac';

type FormValues = {
  name: string;
  remark?: string;
  permission_codes: string[];
};

function toTreeData(
  nodes: ReturnType<typeof flattenPermissionTree>,
): DataNode[] {
  return nodes.map((n) => ({
    title: n.title,
    key: n.key,
    children: n.children?.length ? toTreeData(n.children) : undefined,
  }));
}

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
  const intl = useIntl();
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [treeNodes, setTreeNodes] = useState<DataNode[]>([]);

  const isEdit = !!editing;

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    fetchRolePermissionTree(portalRole)
      .then((nodes) => {
        if (!cancelled) {
          setTreeNodes(toTreeData(flattenPermissionTree(nodes)));
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
    () =>
      isEdit
        ? intl.formatMessage({
            id: 'pages.role.drawer.edit',
            defaultMessage: '编辑角色',
          })
        : intl.formatMessage({
            id: 'pages.role.drawer.create',
            defaultMessage: '新建角色',
          }),
    [intl, isEdit],
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
        message.success(
          intl.formatMessage({
            id: 'pages.role.edit.success',
            defaultMessage: '保存成功',
          }),
        );
      } else {
        await createRole(portalRole, {
          name: values.name.trim(),
          remark: values.remark?.trim(),
          permission_codes: values.permission_codes ?? [],
        });
        message.success(
          intl.formatMessage({
            id: 'pages.role.create.success',
            defaultMessage: '创建成功',
          }),
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
      width={520}
      destroyOnHidden
      onClose={handleClose}
      styles={{ body: { paddingBottom: 80 } }}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={handleClose}>
            {intl.formatMessage({
              id: 'pages.role.drawer.cancel',
              defaultMessage: '取消',
            })}
          </Button>
          <Button type="primary" loading={submitting} onClick={handleSubmit}>
            {intl.formatMessage({
              id: 'pages.role.drawer.submit',
              defaultMessage: '确定',
            })}
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Form.Item
          name="name"
          label={intl.formatMessage({
            id: 'pages.role.field.name',
            defaultMessage: '角色名称',
          })}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'pages.role.field.nameRequired',
                defaultMessage: '请输入角色名称',
              }),
            },
          ]}
        >
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item
          name="remark"
          label={intl.formatMessage({
            id: 'pages.role.field.remark',
            defaultMessage: '备注',
          })}
        >
          <Input.TextArea maxLength={255} rows={2} />
        </Form.Item>
        <Form.Item
          name="permission_codes"
          label={intl.formatMessage({
            id: 'pages.role.field.permissions',
            defaultMessage: '权限',
          })}
          rules={[
            {
              required: true,
              type: 'array',
              min: 1,
              message: intl.formatMessage({
                id: 'pages.role.field.permissionsRequired',
                defaultMessage: '请选择权限',
              }),
            },
          ]}
          valuePropName="checkedKeys"
          trigger="onCheck"
          getValueFromEvent={(checked) =>
            Array.isArray(checked) ? checked : checked.checked
          }
        >
          <Tree
            checkable
            defaultExpandAll
            treeData={treeNodes}
            style={{
              maxHeight: 'calc(100vh - 320px)',
              overflow: 'auto',
              border: '1px solid #f0f0f0',
              borderRadius: 6,
              padding: 8,
            }}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
