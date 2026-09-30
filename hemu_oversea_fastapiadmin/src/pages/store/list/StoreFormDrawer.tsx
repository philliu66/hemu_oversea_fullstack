import { useIntl } from '@umijs/max';
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
  onClose,
  onSuccess,
  onSwitchToEdit,
}: {
  open: boolean;
  mode: StoreDrawerMode;
  storeId?: number;
  onClose: () => void;
  onSuccess: () => void;
  onSwitchToEdit?: () => void;
}) {
  const intl = useIntl();
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
        label: intl.formatMessage({
          id: `pages.store.type.${type}`,
          defaultMessage: STORE_TYPE_LABEL[type],
        }),
        value: type,
      })),
    [intl],
  );

  useEffect(() => {
    if (!open) {
      form.resetFields();
      setMeta({});
      return;
    }
    if (isCreate) {
      form.setFieldsValue({
        storeType: undefined,
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
          message.error(
            intl.formatMessage({
              id: 'pages.store.notFound',
              defaultMessage: '未找到该店铺',
            }),
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
  }, [form, intl, isCreate, message, open, storeId]);

  const title = useMemo(() => {
    if (mode === 'create') {
      return intl.formatMessage({
        id: 'pages.store.drawer.create',
        defaultMessage: '新建店铺',
      });
    }
    if (mode === 'edit') {
      return intl.formatMessage({
        id: 'pages.store.drawer.edit',
        defaultMessage: '编辑店铺',
      });
    }
    return intl.formatMessage({
      id: 'pages.store.drawer.view',
      defaultMessage: '查看店铺',
    });
  }, [intl, mode]);

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
        });
        message.success(
          intl.formatMessage({
            id: 'pages.store.create.success',
            defaultMessage: '创建成功',
          }),
        );
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
        message.success(
          intl.formatMessage({
            id: 'pages.store.edit.success',
            defaultMessage: '保存成功',
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

  const oauthNode =
    meta.oauth_status !== undefined && isOauthStatus(meta.oauth_status) ? (
      <Tag color={STORE_OAUTH_STATUS_COLOR[meta.oauth_status]}>
        {intl.formatMessage({
          id: `pages.store.oauthStatus.${meta.oauth_status}`,
          defaultMessage: STORE_OAUTH_STATUS_LABEL[meta.oauth_status],
        })}
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
      onClose={handleClose}
      styles={{ body: { paddingBottom: 80 } }}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          {readOnly ? (
            <>
              <Button onClick={handleClose}>
                {intl.formatMessage({
                  id: 'pages.store.drawer.close',
                  defaultMessage: '关闭',
                })}
              </Button>
              {onSwitchToEdit ? (
                <Button type="primary" onClick={onSwitchToEdit}>
                  {intl.formatMessage({
                    id: 'pages.store.action.edit',
                    defaultMessage: '编辑',
                  })}
                </Button>
              ) : null}
            </>
          ) : (
            <>
              <Button onClick={handleClose}>
                {intl.formatMessage({
                  id: 'pages.store.drawer.cancel',
                  defaultMessage: '取消',
                })}
              </Button>
              <Button
                type="primary"
                loading={submitting}
                onClick={handleSubmit}
              >
                {intl.formatMessage({
                  id: 'pages.store.drawer.submit',
                  defaultMessage: '确定',
                })}
              </Button>
            </>
          )}
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical" preserve={false}>
          <div className="mb-4 text-base font-medium">
            {intl.formatMessage({
              id: 'pages.store.section.basic',
              defaultMessage: '店铺信息',
            })}
          </div>
          <Form.Item
            name="storeType"
            label={intl.formatMessage({
              id: 'pages.store.field.storeType',
              defaultMessage: '店铺类型',
            })}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'pages.store.field.storeTypeRequired',
                        defaultMessage: '请选择店铺类型',
                      }),
                    },
                  ]
            }
          >
            <Select
              options={storeTypeOptions}
              disabled={readOnly}
              placeholder={intl.formatMessage({
                id: 'pages.store.field.storeTypePlaceholder',
                defaultMessage: '请选择店铺类型',
              })}
            />
          </Form.Item>
          <Form.Item
            name="name"
            label={intl.formatMessage({
              id: 'pages.store.field.name',
              defaultMessage: '店铺名称',
            })}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'pages.store.field.nameRequired',
                        defaultMessage: '请输入店铺名称',
                      }),
                    },
                  ]
            }
          >
            <Input maxLength={100} disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="identifier"
            label={intl.formatMessage({
              id: 'pages.store.field.identifier',
              defaultMessage: '店铺标识',
            })}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'pages.store.field.identifierRequired',
                        defaultMessage: '请输入店铺标识',
                      }),
                    },
                  ]
            }
          >
            <Input maxLength={100} disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="baseDiscount"
            label={intl.formatMessage({
              id: 'pages.store.field.baseDiscount',
              defaultMessage: '基础折扣率',
            })}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'pages.store.field.baseDiscountRequired',
                        defaultMessage: '请输入基础折扣率',
                      }),
                    },
                    {
                      type: 'number',
                      min: 0,
                      max: 0.99,
                      message: intl.formatMessage({
                        id: 'pages.store.field.baseDiscountRange',
                        defaultMessage: '基础折扣率范围为 0～0.99',
                      }),
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
              placeholder={intl.formatMessage({
                id: 'pages.store.field.baseDiscountPlaceholder',
                defaultMessage: '请输入基础折扣率（0～0.99）',
              })}
            />
          </Form.Item>
          <Form.Item
            name="account"
            label={intl.formatMessage({
              id: 'pages.store.field.account',
              defaultMessage: '店铺账号',
            })}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'pages.store.field.accountRequired',
                        defaultMessage: '请输入店铺账号',
                      }),
                    },
                  ]
            }
          >
            <Input maxLength={100} autoComplete="off" disabled={readOnly} />
          </Form.Item>
          <Form.Item
            name="password"
            label={intl.formatMessage({
              id: 'pages.store.field.password',
              defaultMessage: '店铺密码',
            })}
            rules={
              readOnly
                ? undefined
                : [
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'pages.store.field.passwordRequired',
                        defaultMessage: '请输入店铺密码',
                      }),
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
              <Input.Password
                maxLength={255}
                autoComplete="new-password"
              />
            )}
          </Form.Item>

          {!isCreate ? (
            <>
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.store.field.oauthStatus',
                  defaultMessage: '授权状态',
                })}
              >
                {oauthNode}
              </Form.Item>
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.store.field.refreshTokenExpiresAt',
                  defaultMessage: '授权到期',
                })}
              >
                <Input
                  disabled
                  value={formatDateTime(meta.refresh_token_expires_at) || '-'}
                />
              </Form.Item>
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.store.field.createdBy',
                  defaultMessage: '创建人',
                })}
              >
                <Input disabled value={meta.created_by || '-'} />
              </Form.Item>
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.store.field.updatedBy',
                  defaultMessage: '更新人',
                })}
              >
                <Input disabled value={meta.updated_by || '-'} />
              </Form.Item>
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.store.field.createdAt',
                  defaultMessage: '创建时间',
                })}
              >
                <Input
                  disabled
                  value={formatDateTime(meta.created_at) || '-'}
                />
              </Form.Item>
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.store.field.updatedAt',
                  defaultMessage: '更新时间',
                })}
              >
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
