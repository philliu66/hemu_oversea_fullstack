import { PageContainer } from '@ant-design/pro-components';
import { history, useIntl, useParams } from '@umijs/max';
import { App, Button, Card, Descriptions, Popconfirm, Space } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';
import {
  deleteSupplier,
  fetchSupplierDetail,
} from '@/services/admin/suppliers';
import type { SupplierDetailPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import {
  parseSupplierId,
  SUPPLIER_LIST_PATH,
  supplierEditPath,
} from '../utils';

const displayText = (value?: string | number | null) => {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  return value;
};

const SupplierDetailPage: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const { id: idParam } = useParams<{ id: string }>();
  const supplierId = parseSupplierId(idParam);
  const [detail, setDetail] = useState<SupplierDetailPublic>();
  const [loading, setLoading] = useState(true);

  const loadDetail = useCallback(async () => {
    if (!supplierId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchSupplierDetail(supplierId);
      setDetail(data);
    } catch {
      setDetail(undefined);
    } finally {
      setLoading(false);
    }
  }, [supplierId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

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
    <PageContainer
      title={detail?.name}
      onBack={() => history.push(SUPPLIER_LIST_PATH)}
      extra={
        detail ? (
          <Space wrap>
            <Button
              type="primary"
              onClick={() => history.push(supplierEditPath(supplierId))}
            >
              {intl.formatMessage({
                id: 'pages.supplier.action.edit',
                defaultMessage: '编辑',
              })}
            </Button>
            <Popconfirm
              title={intl.formatMessage({
                id: 'pages.supplier.delete.confirm',
                defaultMessage:
                  '确认删除该供应商？删除后其下属账号将一并停用。',
              })}
              onConfirm={async () => {
                try {
                  await deleteSupplier(supplierId);
                  message.success(
                    intl.formatMessage({
                      id: 'pages.supplier.delete.success',
                      defaultMessage: '删除成功',
                    }),
                  );
                  history.replace(SUPPLIER_LIST_PATH);
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button danger>
                {intl.formatMessage({
                  id: 'pages.supplier.action.delete',
                  defaultMessage: '删除',
                })}
              </Button>
            </Popconfirm>
          </Space>
        ) : undefined
      }
    >
      <Card
        title={intl.formatMessage({
          id: 'pages.supplier.section.basic',
          defaultMessage: '供应商信息',
        })}
        loading={loading}
      >
        {detail ? (
          <Descriptions
            column={{ xs: 1, sm: 2 }}
            items={[
              {
                key: 'code',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.code',
                  defaultMessage: '供应商编码',
                }),
                children: detail.code,
              },
              {
                key: 'name',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.name',
                  defaultMessage: '供应商名称',
                }),
                children: detail.name,
              },
              {
                key: 'phone',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.phone',
                  defaultMessage: '联系电话',
                }),
                children: displayText(detail.phone),
              },
              {
                key: 'email',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.email',
                  defaultMessage: '邮件地址',
                }),
                children: displayText(detail.email),
              },
              {
                key: 'created_by',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.createdBy',
                  defaultMessage: '创建人 ID',
                }),
                children: displayText(detail.created_by),
              },
              {
                key: 'created_at',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.createdAt',
                  defaultMessage: '创建时间',
                }),
                children: formatDateTime(detail.created_at),
              },
              {
                key: 'updated_at',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.updatedAt',
                  defaultMessage: '更新时间',
                }),
                children: formatDateTime(detail.updated_at),
              },
            ]}
          />
        ) : (
          !loading &&
          intl.formatMessage({
            id: 'pages.supplier.notFound',
            defaultMessage: '未找到该供应商',
          })
        )}
      </Card>

      <Card
        className="mt-4"
        title={intl.formatMessage({
          id: 'pages.supplier.section.admin',
          defaultMessage: '管理员账号',
        })}
        loading={loading}
      >
        {detail ? (
          <Descriptions
            column={{ xs: 1, sm: 2 }}
            items={[
              {
                key: 'admin_username',
                label: intl.formatMessage({
                  id: 'pages.supplier.field.adminUsername',
                  defaultMessage: '管理员账号',
                }),
                children: displayText(detail.admin_username),
              },
            ]}
          />
        ) : null}
      </Card>
    </PageContainer>
  );
};

export default SupplierDetailPage;
