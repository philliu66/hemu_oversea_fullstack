import {
  App,
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Spin,
  Tag,
} from 'antd';
import React, { useEffect, useMemo, useState } from 'react';
import {
  STORE_OAUTH_STATUS,
  STORE_OAUTH_STATUS_COLOR,
  STORE_OAUTH_STATUS_LABEL,
  STORE_TYPE_LABEL,
  STORE_TYPES,
  type StoreOauthStatusValue,
} from '@/constants/store';
import {
  createStore,
  fetchStoreDetail,
  updateStore,
} from '@/services/admin/stores';
import type { StoreType } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';

export type StoreDrawerMode = 'create' | 'view' | 'edit';

type FormValues = {
  storeType: StoreType;
  name: string;
  identifier: string;
  baseDiscount: number;
  account: string;
  password: string;
};

function isOauthStatus(value: number): value is StoreOauthStatusValue {
  return (
    value === STORE_OAUTH_STATUS.UNAUTHORIZED ||
    value === STORE_OAUTH_STATUS.AUTHORIZED ||
    value === STORE_OAUTH_STATUS.EXPIRED
  );
}

export function StoreFormDrawer({
  open,
  mode,
  storeId,
  supplierId,
  onClose,
  onSuccess,
  onSwitchToEdit,
  lockStoreType = false,
}: {
  open: boolean;
  mode: StoreDrawerMode;
  storeId?: number;
  /** 平台角色创建店铺时传入选中的供应商 */
  supplierId?: number;
  onClose: () => void;
  onSuccess: () => void;
  onSwitchToEdit?: () => void;
  /** 从类型选择进入敦煌新建时锁定类型，避免改成 TikTok */
  lockStoreType?: boolean;
}) {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [meta, setMeta] = useState<{
    oauth_status?: number;
    created_by?: string | null;
    updated_by?: string | null;
    created_at?: string;
    updated_at?: string;
    refresh_token_expires_at?: string | null;
  }>({});

  const readOnly = mode === 'view';
  const isCreate = mode === 'create';

  const storeTypeOptions = useMemo(
    () =>
      STORE_TYPES.map((type) => ({
        label: STORE_TYPE_LABEL[type],
        value: type,
      })),
    [],
  );

  useEffect(() => {
    if (!open) {
      form.resetFields();
      setMeta({});
      return;
    }
    if (isCreate) {
      form.setFieldsValue({
        storeType: lockStoreType ? 'dhgate' : undefined,
        name: undefined,
        identifier: undefined,
        baseDiscount: 0,
        account: undefined,
        password: undefined,
      });
      setMeta({});
      return;
    }
    if (!storeId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetchStoreDetail(storeId)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        form.setFieldsValue({
          storeType: detail.store_type as StoreType,
          name: detail.name,
          identifier: detail.identifier,
          baseDiscount: Number(detail.base_discount ?? 0),
          account: detail.account,
          password: detail.password,
        });
        setMeta({
          oauth_status: detail.oauth_status,
          created_by: detail.created_by,
          updated_by: detail.updated_by,
          created_at: detail.created_at,
          updated_at: detail.updated_at,
          refresh_token_expires_at: detail.refresh_token_expires_at,
        });
      })
      .catch(() => {
        if (!cancelled) {
          message.error('未找到该店铺');
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
  }, [form, isCreate, lockStoreType, message, open, storeId]);

  const title = useMemo(() => {
    if (mode === 'create') {
      return '新建店铺';
    }
    if (mode === 'edit') {
      return '编辑店铺';
    }
    return '查看店铺';
  }, [mode]);

  const handleClose = () => {
    form.resetFields();
    setMeta({});
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
        await createStore({
          store_type: values.storeType,
          name: values.name.trim(),
          identifier: values.identifier.trim(),
          base_discount: values.baseDiscount,
          account: values.account.trim(),
          password: values.password,
          supplier_id: supplierId,
        });
        message.success('创建成功');
      } else if (storeId) {
        await updateStore({
          id: storeId,
          store_type: values.storeType,
          name: values.name.trim(),
          identifier: values.identifier.trim(),
          base_discount: values.baseDiscount,
          account: values.account.trim(),
          password: values.password,
        });
        message.success('保存成功');
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

  const oauthNode =
    meta.oauth_status !== undefined && isOauthStatus(meta.oauth_status) ? (
      <Tag color={STORE_OAUTH_STATUS_COLOR[meta.oauth_status]}>
        {STORE_OAUTH_STATUS_LABEL[meta.oauth_status]}
      </Tag>
    ) : (
      '-'
    );

  return (
    <Drawer
      title={title}
      open={open}
      width={480}
      destroyOnHidden
      maskClosable={false}
      onClose={handleClose}
      styles={{ body: { paddingBottom: 80 } }}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          {readOnly ? (
            <>
              <Button onClick={handleClose}>{'关闭'}</Button>
              {onSwitchToEdit ? (
                <Button type="primary" onClick={onSwitchToEdit}>
                  {'编辑'}
                </Button>
              ) : null}
            </>
          ) : (
            <>
              <Button onClick={handleClose}>{'取消'}</Button>
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
          <div className="mb-4 text-base font-medium">{'店铺信息'}</div>
          <Form.Item
            name="storeType"
            label={'店铺类型'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请选择店铺类型',
                    },
                  ]
            }
          >
            <Select
              options={storeTypeOptions}
              disabled={readOnly || lockStoreType}
              placeholder={'请选择店铺类型'}
            />
          </Form.Item>
          <Form.Item
            name="name"
            label={'店铺名称'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入店铺名称',
                    },
                  ]
            }
          >
            <Input maxLength={100} disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="identifier"
            label={'店铺标识'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入店铺标识',
                    },
                  ]
            }
          >
            <Input maxLength={100} disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="baseDiscount"
            label={'基础折扣率'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入基础折扣率',
                    },
                    {
                      type: 'number',
                      min: 0,
                      max: 0.99,
                      message: '基础折扣率范围为 0～0.99',
                    },
                  ]
            }
          >
            <InputNumber
              min={0}
              max={0.99}
              step={0.01}
              precision={2}
              style={{ width: '100%' }}
              disabled={readOnly}
              placeholder={'请输入基础折扣率（0～0.99）'}
            />
          </Form.Item>
          <Form.Item
            name="account"
            label={'店铺账号'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入店铺账号',
                    },
                  ]
            }
          >
            <Input maxLength={100} autoComplete="off" disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="password"
            label={'店铺密码'}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: '请输入店铺密码',
                    },
                  ]
            }
          >
            {readOnly ? (
              <Input.Password
                visibilityToggle
                disabled
                autoComplete="new-password"
              />
            ) : (
              <Input.Password maxLength={255} autoComplete="new-password" />
            )}
          </Form.Item>

          {!isCreate ? (
            <>
              <Form.Item label={'授权状态'}>{oauthNode}</Form.Item>
              <Form.Item label={'授权到期'}>
                <Input
                  disabled
                  value={formatDateTime(meta.refresh_token_expires_at) || '-'}
                />
              </Form.Item>
              <Form.Item label={'创建人'}>
                <Input disabled value={meta.created_by || '-'} />
              </Form.Item>
              <Form.Item label={'更新人'}>
                <Input disabled value={meta.updated_by || '-'} />
              </Form.Item>
              <Form.Item label={'创建时间'}>
                <Input
                  disabled
                  value={formatDateTime(meta.created_at) || '-'}
                />
              </Form.Item>
              <Form.Item label={'更新时间'}>
                <Input
                  disabled
                  value={formatDateTime(meta.updated_at) || '-'}
                />
              </Form.Item>
            </>
          ) : null}
        </Form>
      </Spin>
    </Drawer>
  );
}
