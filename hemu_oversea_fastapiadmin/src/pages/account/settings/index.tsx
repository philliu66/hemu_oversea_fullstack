import { PageContainer } from '@ant-design/pro-components';
import { history, useIntl, useModel } from '@umijs/max';
import {
  App,
  Avatar,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  Modal,
  Space,
  Tag,
} from 'antd';
import React, {
  startTransition,
  useCallback,
  useEffect,
  useState,
} from 'react';
import { adminChangePassword, fetchAdminMe } from '@/services/admin/auth';
import type { UserPublic } from '@/types/api';
import { clearTokens } from '@/utils/authToken';
import { formatDateTime } from '@/utils/datetime';
import { mapUserToCurrentUser } from '@/utils/userMapper';

type PasswordFormValues = {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
};

const AccountSettings: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const { setInitialState } = useModel('@@initialState');
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserPublic | null>(null);
  const [pwdOpen, setPwdOpen] = useState(false);
  const [pwdSubmitting, setPwdSubmitting] = useState(false);
  const [pwdForm] = Form.useForm<PasswordFormValues>();

  const loadUser = useCallback(async () => {
    setLoading(true);
    try {
      const profile = await fetchAdminMe();
      setUser(profile);
      startTransition(() => {
        setInitialState((s) => ({
          ...s,
          currentUser: mapUserToCurrentUser(profile),
        }));
      });
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [setInitialState]);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  const roleLabel = (role?: string) => {
    if (!role) return '-';
    return intl.formatMessage({
      id: `pages.account.role.${role}`,
      defaultMessage: role,
    });
  };

  const closePwdModal = () => {
    setPwdOpen(false);
    pwdForm.resetFields();
  };

  const handleChangePassword = async () => {
    try {
      const values = await pwdForm.validateFields();
      if (values.newPassword !== values.confirmPassword) {
        pwdForm.setFields([
          {
            name: 'confirmPassword',
            errors: [
              intl.formatMessage({
                id: 'pages.account.password.confirmMismatch',
                defaultMessage: '两次输入的新密码不一致',
              }),
            ],
          },
        ]);
        return;
      }

      setPwdSubmitting(true);
      await adminChangePassword({
        oldPassword: values.oldPassword,
        newPassword: values.newPassword,
      });

      message.success(
        intl.formatMessage({
          id: 'pages.account.password.success',
          defaultMessage: '修改成功',
        }),
      );
      closePwdModal();
      clearTokens();
      startTransition(() => {
        setInitialState((s) => ({ ...s, currentUser: undefined }));
      });
      history.replace('/user/login');
    } catch {
      // 校验失败或接口错误：接口错误由全局拦截器提示
    } finally {
      setPwdSubmitting(false);
    }
  };

  return (
    <PageContainer
      title={intl.formatMessage({
        id: 'menu.account.settings',
        defaultMessage: '个人设置',
      })}
      extra={
        user ? (
          <Button type="primary" onClick={() => setPwdOpen(true)}>
            {intl.formatMessage({
              id: 'pages.account.password.action',
              defaultMessage: '修改密码',
            })}
          </Button>
        ) : null
      }
    >
      <Card loading={loading}>
        {!loading && !user ? (
          <Empty
            description={intl.formatMessage({
              id: 'pages.account.loadFailed',
              defaultMessage: '用户信息加载失败',
            })}
          />
        ) : (
          <>
            <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
              <Avatar size={72} src={user?.avatar_url || undefined}>
                {(user?.nickname || user?.username || '?')
                  .slice(0, 1)
                  .toUpperCase()}
              </Avatar>
              <div>
                <div style={{ fontSize: 20, fontWeight: 600 }}>
                  {user?.nickname || user?.username || '-'}
                </div>
                <div style={{ color: 'rgba(0,0,0,0.45)', marginTop: 4 }}>
                  @{user?.username || '-'}
                </div>
                <div style={{ marginTop: 8 }}>
                  {user?.is_active ? (
                    <Tag color="success">
                      {intl.formatMessage({
                        id: 'pages.account.status.active',
                        defaultMessage: '启用',
                      })}
                    </Tag>
                  ) : (
                    <Tag color="default">
                      {intl.formatMessage({
                        id: 'pages.account.status.inactive',
                        defaultMessage: '停用',
                      })}
                    </Tag>
                  )}
                  {user?.role ? <Tag>{roleLabel(user.role)}</Tag> : null}
                </div>
              </div>
            </div>

            <Descriptions
              title={intl.formatMessage({
                id: 'pages.account.basicInfo',
                defaultMessage: '基本信息',
              })}
              column={{ xs: 1, sm: 1, md: 2 }}
              bordered
              size="middle"
            >
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.username',
                  defaultMessage: '账号',
                })}
              >
                {user?.username || '-'}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.nickname',
                  defaultMessage: '昵称',
                })}
              >
                {user?.nickname || '-'}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.email',
                  defaultMessage: '邮箱',
                })}
              >
                {user?.email || '-'}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.phone',
                  defaultMessage: '手机号',
                })}
              >
                {user?.phone || '-'}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.role',
                  defaultMessage: '角色',
                })}
              >
                {roleLabel(user?.role)}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.status',
                  defaultMessage: '状态',
                })}
              >
                {user?.is_active
                  ? intl.formatMessage({
                      id: 'pages.account.status.active',
                      defaultMessage: '启用',
                    })
                  : intl.formatMessage({
                      id: 'pages.account.status.inactive',
                      defaultMessage: '停用',
                    })}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.createdAt',
                  defaultMessage: '创建时间',
                })}
              >
                {formatDateTime(user?.created_at)}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.account.field.updatedAt',
                  defaultMessage: '更新时间',
                })}
              >
                {formatDateTime(user?.updated_at)}
              </Descriptions.Item>
            </Descriptions>
          </>
        )}
      </Card>

      <Modal
        title={intl.formatMessage({
          id: 'pages.account.password.action',
          defaultMessage: '修改密码',
        })}
        open={pwdOpen}
        onCancel={closePwdModal}
        destroyOnHidden
        footer={
          <Space>
            <Button onClick={closePwdModal}>
              {intl.formatMessage({
                id: 'pages.account.password.cancel',
                defaultMessage: '取消',
              })}
            </Button>
            <Button
              type="primary"
              loading={pwdSubmitting}
              onClick={() => void handleChangePassword()}
            >
              {intl.formatMessage({
                id: 'pages.account.password.submit',
                defaultMessage: '确认修改',
              })}
            </Button>
          </Space>
        }
      >
        <Form form={pwdForm} layout="vertical" autoComplete="off">
          <Form.Item
            name="oldPassword"
            label={intl.formatMessage({
              id: 'pages.account.password.old',
              defaultMessage: '旧密码',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.account.password.oldRequired',
                  defaultMessage: '请输入旧密码',
                }),
              },
            ]}
          >
            <Input.Password
              placeholder={intl.formatMessage({
                id: 'pages.account.password.oldPlaceholder',
                defaultMessage: '请输入旧密码',
              })}
            />
          </Form.Item>
          <Form.Item
            name="newPassword"
            label={intl.formatMessage({
              id: 'pages.account.password.new',
              defaultMessage: '新密码',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.account.password.newRequired',
                  defaultMessage: '请输入新密码',
                }),
              },
              {
                min: 6,
                message: intl.formatMessage({
                  id: 'pages.account.password.newMin',
                  defaultMessage: '新密码至少 6 位',
                }),
              },
            ]}
          >
            <Input.Password
              placeholder={intl.formatMessage({
                id: 'pages.account.password.newPlaceholder',
                defaultMessage: '请输入新密码',
              })}
            />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label={intl.formatMessage({
              id: 'pages.account.password.confirm',
              defaultMessage: '确认新密码',
            })}
            dependencies={['newPassword']}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.account.password.confirmRequired',
                  defaultMessage: '请再次输入新密码',
                }),
              },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error(
                      intl.formatMessage({
                        id: 'pages.account.password.confirmMismatch',
                        defaultMessage: '两次输入的新密码不一致',
                      }),
                    ),
                  );
                },
              }),
            ]}
          >
            <Input.Password
              placeholder={intl.formatMessage({
                id: 'pages.account.password.confirmPlaceholder',
                defaultMessage: '请再次输入新密码',
              })}
            />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default AccountSettings;
