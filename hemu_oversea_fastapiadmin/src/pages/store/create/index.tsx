import {
  PageContainer,
  ProForm,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { history, useIntl } from '@umijs/max';
import { App, Card } from 'antd';
import React from 'react';
import { STORE_TYPE_LABEL, STORE_TYPES } from '@/constants/store';
import { createStore } from '@/services/admin/stores';
import type { StoreType } from '@/types/api';
import { STORE_LIST_PATH, storeDetailPath } from '../utils';

type CreateFormValues = {
  storeType: StoreType;
  name: string;
  identifier: string;
  account: string;
  password: string;
};

const StoreCreate: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();

  const storeTypeOptions = STORE_TYPES.map((type) => ({
    label: intl.formatMessage({
      id: `pages.store.type.${type}`,
      defaultMessage: STORE_TYPE_LABEL[type],
    }),
    value: type,
  }));

  return (
    <PageContainer onBack={() => history.push(STORE_LIST_PATH)}>
      <Card>
        <ProForm<CreateFormValues>
          className="max-w-xl"
          submitter={{
            searchConfig: {
              submitText: intl.formatMessage({
                id: 'pages.store.form.submit',
                defaultMessage: '提交',
              }),
              resetText: intl.formatMessage({
                id: 'pages.store.form.cancel',
                defaultMessage: '取消',
              }),
            },
            onReset: () => history.push(STORE_LIST_PATH),
          }}
          onFinish={async (values) => {
            try {
              const result = await createStore({
                store_type: values.storeType,
                name: values.name.trim(),
                identifier: values.identifier.trim(),
                account: values.account.trim(),
                password: values.password,
              });
              message.success(
                intl.formatMessage({
                  id: 'pages.store.create.success',
                  defaultMessage: '创建成功',
                }),
              );
              history.replace(storeDetailPath(result.id));
              return true;
            } catch {
              return false;
            }
          }}
        >
          <ProFormSelect
            name="storeType"
            label={intl.formatMessage({
              id: 'pages.store.field.storeType',
              defaultMessage: '店铺类型',
            })}
            options={storeTypeOptions}
            placeholder={intl.formatMessage({
              id: 'pages.store.field.storeTypePlaceholder',
              defaultMessage: '请选择店铺类型',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.store.field.storeTypeRequired',
                  defaultMessage: '请选择店铺类型',
                }),
              },
            ]}
          />
          <ProFormText
            name="name"
            label={intl.formatMessage({
              id: 'pages.store.field.name',
              defaultMessage: '店铺名称',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.store.field.namePlaceholder',
              defaultMessage: '请输入店铺名称',
            })}
            fieldProps={{ maxLength: 100 }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.store.field.nameRequired',
                  defaultMessage: '请输入店铺名称',
                }),
              },
            ]}
          />
          <ProFormText
            name="identifier"
            label={intl.formatMessage({
              id: 'pages.store.field.identifier',
              defaultMessage: '店铺标识',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.store.field.identifierPlaceholder',
              defaultMessage: '请输入店铺标识',
            })}
            fieldProps={{ maxLength: 100 }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.store.field.identifierRequired',
                  defaultMessage: '请输入店铺标识',
                }),
              },
            ]}
          />
          <ProFormText
            name="account"
            label={intl.formatMessage({
              id: 'pages.store.field.account',
              defaultMessage: '店铺账号',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.store.field.accountPlaceholder',
              defaultMessage: '请输入店铺账号',
            })}
            fieldProps={{ maxLength: 100, autoComplete: 'off' }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.store.field.accountRequired',
                  defaultMessage: '请输入店铺账号',
                }),
              },
            ]}
          />
          <ProFormText.Password
            name="password"
            label={intl.formatMessage({
              id: 'pages.store.field.password',
              defaultMessage: '店铺密码',
            })}
            placeholder={intl.formatMessage({
              id: 'pages.store.field.passwordPlaceholder',
              defaultMessage: '请输入店铺密码',
            })}
            fieldProps={{ maxLength: 255, autoComplete: 'new-password' }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'pages.store.field.passwordRequired',
                  defaultMessage: '请输入店铺密码',
                }),
              },
            ]}
          />
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default StoreCreate;
