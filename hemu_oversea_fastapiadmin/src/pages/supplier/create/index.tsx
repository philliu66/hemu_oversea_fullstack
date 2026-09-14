import {
  PageContainer,
  ProForm,
  ProFormText,
} from '@ant-design/pro-components';
import { history, useIntl } from '@umijs/max';
import { App, Card } from 'antd';
import React from 'react';
import { createSupplier } from '@/services/admin/suppliers';
import {
  confirmPasswordValidator,
  SUPPLIER_LIST_PATH,
  supplierDetailPath,
} from '../utils';

type CreateFormValues = {
  name: string;
  phone: string;
  email: string;
  adminUsername: string;
  adminPassword: string;
  confirmPassword: string;
};

const SupplierCreate: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();

  return (
    <PageContainer onBack={() => history.push(SUPPLIER_LIST_PATH)}>
      <Card>
        <ProForm<CreateFormValues>
          className="max-w-xl"
          submitter={{
            searchConfig: {
              submitText: intl.formatMessage({
                id: 'pages.supplier.form.submit',
                defaultMessage: '提交',
              }),
              resetText: intl.formatMessage({
                id: 'pages.supplier.form.cancel',
                defaultMessage: '取消',
              }),
            },
            onReset: () => history.push(SUPPLIER_LIST_PATH),
          }}
          onFinish={async (values) => {
            try {
              const result = await createSupplier({
                name: values.name.trim(),
                phone: values.phone.trim(),
                email: values.email.trim(),
                admin_username: values.adminUsername.trim(),
                admin_password: values.adminPassword,
              });
              message.success(
                intl.formatMessage({
                  id: 'pages.supplier.create.success',
                  defaultMessage: '创建成功',
                }),
              );
              history.replace(supplierDetailPath(result.id));
              return true;
            } catch {
              return false;
            }
          }}
        >
          <div className="mb-4 text-base font-medium">
            {intl.formatMessage({
              id: 'pages.supplier.section.basic',
              defaultMessage: '供应商信息',
            })}
          </div>
          <ProFormText
            name="name"
            label={intl.formatMessage({
              id: 'pages.supplier.field.name',
              defaultMessage: '供应商名称',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.supplier.field.namePlaceholder',
              defaultMessage: '请输入供应商名称',
            })}
            fieldProps={{ maxLength: 100 }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.nameRequired',
                  defaultMessage: '请输入供应商名称',
                }),
              },
            ]}
          />
          <ProFormText
            name="phone"
            label={intl.formatMessage({
              id: 'pages.supplier.field.phone',
              defaultMessage: '联系电话',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.supplier.field.phonePlaceholder',
              defaultMessage: '请输入联系电话',
            })}
            fieldProps={{ maxLength: 20 }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.phoneRequired',
                  defaultMessage: '请输入联系电话',
                }),
              },
              {
                min: 5,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.phoneMin',
                  defaultMessage: '联系电话至少 5 位',
                }),
              },
            ]}
          />
          <ProFormText
            name="email"
            label={intl.formatMessage({
              id: 'pages.supplier.field.email',
              defaultMessage: '邮件地址',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.supplier.field.emailPlaceholder',
              defaultMessage: '请输入邮件地址',
            })}
            fieldProps={{ maxLength: 255 }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.emailRequired',
                  defaultMessage: '请输入邮件地址',
                }),
              },
              {
                type: 'email',
                message: intl.formatMessage({
                  id: 'pages.supplier.field.emailInvalid',
                  defaultMessage: '请输入正确的邮箱',
                }),
              },
            ]}
          />

          <div className="mb-4 mt-6 text-base font-medium">
            {intl.formatMessage({
              id: 'pages.supplier.section.admin',
              defaultMessage: '管理员账号',
            })}
          </div>
          <ProFormText
            name="adminUsername"
            label={intl.formatMessage({
              id: 'pages.supplier.field.adminUsername',
              defaultMessage: '管理员账号',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.supplier.field.adminUsernamePlaceholder',
              defaultMessage: '请输入管理员账号',
            })}
            fieldProps={{ maxLength: 50, autoComplete: 'off' }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.adminUsernameRequired',
                  defaultMessage: '请输入管理员账号',
                }),
              },
              {
                min: 3,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.adminUsernameMin',
                  defaultMessage: '管理员账号至少 3 位',
                }),
              },
            ]}
          />
          <ProFormText.Password
            name="adminPassword"
            label={intl.formatMessage({
              id: 'pages.supplier.field.adminPassword',
              defaultMessage: '管理员密码',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.supplier.field.adminPasswordPlaceholder',
              defaultMessage: '请输入管理员密码',
            })}
            fieldProps={{ autoComplete: 'new-password' }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.adminPasswordRequired',
                  defaultMessage: '请输入管理员密码',
                }),
              },
              {
                min: 6,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.adminPasswordMin',
                  defaultMessage: '密码至少 6 位',
                }),
              },
            ]}
          />
          <ProFormText.Password
            name="confirmPassword"
            label={intl.formatMessage({
              id: 'pages.supplier.field.confirmPassword',
              defaultMessage: '确认密码',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.supplier.field.confirmPasswordPlaceholder',
              defaultMessage: '请再次输入管理员密码',
            })}
            dependencies={['adminPassword']}
            fieldProps={{ autoComplete: 'new-password' }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.supplier.field.confirmPasswordRequired',
                  defaultMessage: '请再次输入管理员密码',
                }),
              },
              ({ getFieldValue }) => ({
                validator: confirmPasswordValidator(getFieldValue),
              }),
            ]}
          />
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default SupplierCreate;
