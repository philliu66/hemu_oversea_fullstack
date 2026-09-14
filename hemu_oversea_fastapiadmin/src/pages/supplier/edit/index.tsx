import {
  PageContainer,
  ProForm,
  ProFormText,
} from '@ant-design/pro-components';
import { history, useIntl, useParams } from '@umijs/max';
import { App, Card } from 'antd';
import React from 'react';
import {
  fetchSupplierDetail,
  updateSupplier,
} from '@/services/admin/suppliers';
import {
  parseSupplierId,
  SUPPLIER_LIST_PATH,
  supplierDetailPath,
} from '../utils';

type EditFormValues = {
  code?: string;
  name: string;
  phone: string;
  email: string;
};

const SupplierEdit: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const { id: idParam } = useParams<{ id: string }>();
  const supplierId = parseSupplierId(idParam);

  if (!supplierId) {
    return (
      <PageContainer onBack={() => history.push(SUPPLIER_LIST_PATH)}>
        <Card>
          {intl.formatMessage({
            id: 'pages.supplier.invalidId',
            defaultMessage: '供应商 ID 无效',
          })}
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer onBack={() => history.push(supplierDetailPath(supplierId))}>
      <Card>
        <ProForm<EditFormValues>
          className="max-w-xl"
          params={{ supplierId }}
          request={async () => {
            const detail = await fetchSupplierDetail(supplierId);
            return {
              code: detail.code,
              name: detail.name,
              phone: detail.phone,
              email: detail.email,
            };
          }}
          submitter={{
            searchConfig: {
              submitText: intl.formatMessage({
                id: 'pages.supplier.form.save',
                defaultMessage: '保存',
              }),
              resetText: intl.formatMessage({
                id: 'pages.supplier.form.cancel',
                defaultMessage: '取消',
              }),
            },
            onReset: () => history.push(supplierDetailPath(supplierId)),
          }}
          onFinish={async (values) => {
            try {
              await updateSupplier({
                id: supplierId,
                name: values.name.trim(),
                phone: values.phone.trim(),
                email: values.email.trim(),
              });
              message.success(
                intl.formatMessage({
                  id: 'pages.supplier.edit.success',
                  defaultMessage: '保存成功',
                }),
              );
              history.replace(supplierDetailPath(supplierId));
              return true;
            } catch {
              return false;
            }
          }}
        >
          <ProFormText
            name="code"
            label={intl.formatMessage({
              id: 'pages.supplier.field.code',
              defaultMessage: '供应商编码',
            })}
            disabled
          />
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
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default SupplierEdit;
