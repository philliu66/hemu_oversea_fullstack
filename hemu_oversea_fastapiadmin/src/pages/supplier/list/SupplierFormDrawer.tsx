import { App, Button, Drawer, Form, Input, Space, Spin, Tree } from 'antd';
import type { DataNode } from 'antd/es/tree';
import React, { useEffect, useMemo, useState } from 'react';
import {
  fetchSupplierAssignablePermissionTree,
  flattenPermissionTree,
} from '@/services/admin/rbac';
import {
  createSupplier,
  fetchSupplierDetail,
  updateSupplier,
} from '@/services/admin/suppliers';
import { confirmPasswordValidator } from '../utils';

export type SupplierDrawerMode = 'create' | 'view' | 'edit';

type FormValues = {
  code?: string;
  name: string;
  phone: string;
  email: string;
  permission_codes: string[];
  adminUsername: string;
  adminPassword?: string;
  confirmPassword?: string;
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

export function SupplierFormDrawer({
  open,
  mode,
  supplierId,
  onClose,
  onSuccess,
  onSwitchToEdit,
}: {
  open: boolean;
  mode: SupplierDrawerMode;
  supplierId?: number;
  onClose: () => void;
  onSuccess: () => void;
  onSwitchToEdit?: () => void;
}) {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [treeNodes, setTreeNodes] = useState<DataNode[]>([]);

  const readOnly = mode === 'view';
  const isCreate = mode === 'create';

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    fetchSupplierAssignablePermissionTree()
      .then((nodes) => {
        if (!cancelled) {
          setTreeNodes(toTreeData(flattenPermissionTree(nodes)));
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open) {
      form.resetFields();
      return;
    }
    if (isCreate) {
      form.setFieldsValue({
        code: undefined,
        name: undefined,
        phone: undefined,
        email: undefined,
        permission_codes: [],
        adminUsername: undefined,
        adminPassword: undefined,
        confirmPassword: undefined,
      });
      return;
    }
    if (!supplierId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetchSupplierDetail(supplierId)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        form.setFieldsValue({
          code: detail.code,
          name: detail.name,
          phone: detail.phone,
          email: detail.email,
          permission_codes: detail.permission_codes ?? [],
          adminUsername: detail.admin_username || '',
          adminPassword: undefined,
          confirmPassword: undefined,
        });
      })
      .catch(() => {
        if (!cancelled) {
          message.error(
            '未找到该供应商',
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [form, isCreate, message, open, supplierId]);

  const title = useMemo(() => {
    if (mode === 'create') {
      return '新建供应商';
    }
    if (mode === 'edit') {
      return '编辑供应商';
    }
    return '查看供应商';
  }, [mode]);

  const handleClose = () => {
    form.resetFields();
    onClose();
  };

  const handleSubmit = async () => {
    if (readOnly) {
      return;
    }
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (isCreate) {
        await createSupplier({
          name: values.name.trim(),
          phone: values.phone.trim(),
          email: values.email.trim(),
          admin_username: values.adminUsername.trim(),
          admin_password: values.adminPassword || '',
          permission_codes: values.permission_codes ?? [],
        });
        message.success(
          '创建成功',
        );
      } else if (supplierId) {
        await updateSupplier({
          id: supplierId,
          name: values.name.trim(),
          phone: values.phone.trim(),
          email: values.email.trim(),
          permission_codes: values.permission_codes ?? [],
        });
        message.success(
          '保存成功',
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
      width={560}
      destroyOnHidden
      maskClosable={false}
      onClose={handleClose}
      styles={{ body: { paddingBottom: 80 } }}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          {readOnly ? (
            <>
              <Button onClick={handleClose}>
                {'关闭'}
              </Button>
              {onSwitchToEdit ? (
                <Button type="primary" onClick={onSwitchToEdit}>
                  {'编辑'}
                </Button>
              ) : null}
            </>
          ) : (
            <>
              <Button onClick={handleClose}>
                {'取消'}
              </Button>
              <Button
                type="primary"
                loading={submitting}
                onClick={handleSubmit}
              >
                {'确定'}
              </Button>
            </>
          )}
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical" preserve={false}>
          <div className="mb-4 text-base font-medium">
            {'供应商信息'}
          </div>
          {!isCreate ? (
            <Form.Item
              name="code"
              label={'供应商编码'}
            >
              <Input disabled />
            </Form.Item>
          ) : null}
          <Form.Item
            name="name"
            label={'供应商名称'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入供应商名称',
                    },
                  ]
            }
          >
            <Input maxLength={100} disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="phone"
            label={'联系电话'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入联系电话',
                    },
                    {
                      min: 5,
                      message: '联系电话至少 5 位',
                    },
                  ]
            }
          >
            <Input maxLength={20} disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="email"
            label={'邮件地址'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入邮件地址',
                    },
                    {
                      type: 'email',
                      message: '请输入正确的邮箱',
                    },
                  ]
            }
          >
            <Input maxLength={255} disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="permission_codes"
            label={'开通权限'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      type: 'array',
                      min: 1,
                      message: '请选择开通权限',
                    },
                  ]
            }
            valuePropName="checkedKeys"
            trigger="onCheck"
            getValueFromEvent={(checked) =>
              Array.isArray(checked) ? checked : checked.checked
            }
          >
            <Tree
              checkable
              disabled={readOnly}
              defaultExpandAll
              treeData={treeNodes}
              style={{
                maxHeight: 280,
                overflow: 'auto',
                border: '1px solid #f0f0f0',
                borderRadius: 6,
                padding: 8,
              }}
            />
          </Form.Item>

          <div className="mb-4 mt-6 text-base font-medium">
            {'管理员设置'}
          </div>
          <Form.Item
            name="adminUsername"
            label={'管理员账号'}
            rules={
              isCreate
                ? [
                    {
                      required: true,
                      message: '请输入管理员账号',
                    },
                    {
                      min: 3,
                      message: '账号至少 3 位',
                    },
                  ]
                : undefined
            }
          >
            <Input maxLength={50} disabled={!isCreate} />
          </Form.Item>
          {isCreate ? (
            <>
              <Form.Item
                name="adminPassword"
                label={'管理员密码'}
                rules={[
                  {
                    required: true,
                    message: '请输入管理员密码',
                  },
                  {
                    min: 6,
                    message: '密码至少 6 位',
                  },
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Form.Item
                name="confirmPassword"
                label={'确认密码'}
                dependencies={['adminPassword']}
                rules={[
                  {
                    required: true,
                    message: '请再次输入管理员密码',
                  },
                  ({ getFieldValue }) => ({
                    validator: confirmPasswordValidator(getFieldValue),
                  }),
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
            </>
          ) : null}
        </Form>
      </Spin>
    </Drawer>
  );
}
