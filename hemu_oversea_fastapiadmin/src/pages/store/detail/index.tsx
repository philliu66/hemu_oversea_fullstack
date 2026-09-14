import { PageContainer } from '@ant-design/pro-components';
import { history, useIntl, useParams } from '@umijs/max';
import {
  App,
  Button,
  Card,
  Descriptions,
  Popconfirm,
  Space,
  Tag,
  Typography,
} from 'antd';
import React, { useCallback, useEffect, useState } from 'react';
import {
  STORE_OAUTH_STATUS,
  STORE_OAUTH_STATUS_COLOR,
  STORE_OAUTH_STATUS_LABEL,
  STORE_TYPE_LABEL,
  STORE_TYPES,
  type StoreOauthStatusValue,
} from '@/constants/store';
import { deleteStore, fetchStoreDetail } from '@/services/admin/stores';
import type { StoreDetailPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { parseStoreId, STORE_LIST_PATH, storeEditPath } from '../utils';

const displayText = (value?: string | number | null) => {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  return value;
};

function isOauthStatus(value: number): value is StoreOauthStatusValue {
  return (
    value === STORE_OAUTH_STATUS.UNAUTHORIZED ||
    value === STORE_OAUTH_STATUS.AUTHORIZED ||
    value === STORE_OAUTH_STATUS.EXPIRED
  );
}

const StoreDetailPage: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const { id: idParam } = useParams<{ id: string }>();
  const storeId = parseStoreId(idParam);
  const [detail, setDetail] = useState<StoreDetailPublic>();
  const [loading, setLoading] = useState(true);

  const loadDetail = useCallback(async () => {
    if (!storeId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchStoreDetail(storeId);
      setDetail(data);
    } catch {
      setDetail(undefined);
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const storeTypeLabel = (type?: string) => {
    if (!type) return '-';
    if (STORE_TYPES.includes(type as (typeof STORE_TYPES)[number])) {
      return intl.formatMessage({
        id: `pages.store.type.${type}`,
        defaultMessage: STORE_TYPE_LABEL[type as (typeof STORE_TYPES)[number]],
      });
    }
    return type;
  };

  const oauthStatusNode = (status?: number) => {
    if (status === undefined || !isOauthStatus(status)) {
      return '-';
    }
    return (
      <Tag color={STORE_OAUTH_STATUS_COLOR[status]}>
        {intl.formatMessage({
          id: `pages.store.oauthStatus.${status}`,
          defaultMessage: STORE_OAUTH_STATUS_LABEL[status],
        })}
      </Tag>
    );
  };

  if (!storeId) {
    return (
      <PageContainer onBack={() => history.push(STORE_LIST_PATH)}>
        <Card>
          {intl.formatMessage({
            id: 'pages.store.invalidId',
            defaultMessage: '店铺 ID 无效',
          })}
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={detail?.name}
      onBack={() => history.push(STORE_LIST_PATH)}
      extra={
        detail ? (
          <Space wrap>
            <Button
              type="primary"
              onClick={() => history.push(storeEditPath(storeId))}
            >
              {intl.formatMessage({
                id: 'pages.store.action.edit',
                defaultMessage: '编辑',
              })}
            </Button>
            <Popconfirm
              title={intl.formatMessage({
                id: 'pages.store.delete.confirm',
                defaultMessage: '确认删除该店铺？',
              })}
              onConfirm={async () => {
                try {
                  await deleteStore(storeId);
                  message.success(
                    intl.formatMessage({
                      id: 'pages.store.delete.success',
                      defaultMessage: '删除成功',
                    }),
                  );
                  history.replace(STORE_LIST_PATH);
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button danger>
                {intl.formatMessage({
                  id: 'pages.store.action.delete',
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
          id: 'pages.store.section.basic',
          defaultMessage: '店铺信息',
        })}
        loading={loading}
      >
        {detail ? (
          <Descriptions
            column={{ xs: 1, sm: 2 }}
            items={[
              {
                key: 'store_type',
                label: intl.formatMessage({
                  id: 'pages.store.field.storeType',
                  defaultMessage: '店铺类型',
                }),
                children: storeTypeLabel(detail.store_type),
              },
              {
                key: 'name',
                label: intl.formatMessage({
                  id: 'pages.store.field.name',
                  defaultMessage: '店铺名称',
                }),
                children: detail.name,
              },
              {
                key: 'identifier',
                label: intl.formatMessage({
                  id: 'pages.store.field.identifier',
                  defaultMessage: '店铺标识',
                }),
                children: displayText(detail.identifier),
              },
              {
                key: 'oauth_status',
                label: intl.formatMessage({
                  id: 'pages.store.field.oauthStatus',
                  defaultMessage: '授权状态',
                }),
                children: oauthStatusNode(detail.oauth_status),
              },
              {
                key: 'account',
                label: intl.formatMessage({
                  id: 'pages.store.field.account',
                  defaultMessage: '店铺账号',
                }),
                children: displayText(detail.account),
              },
              {
                key: 'password',
                label: intl.formatMessage({
                  id: 'pages.store.field.password',
                  defaultMessage: '店铺密码',
                }),
                children: (
                  <Typography.Text copyable={{ text: detail.password }}>
                    {detail.password}
                  </Typography.Text>
                ),
              },
              {
                key: 'created_by',
                label: intl.formatMessage({
                  id: 'pages.store.field.createdBy',
                  defaultMessage: '创建人',
                }),
                children: displayText(detail.created_by),
              },
              {
                key: 'updated_by',
                label: intl.formatMessage({
                  id: 'pages.store.field.updatedBy',
                  defaultMessage: '更新人',
                }),
                children: displayText(detail.updated_by),
              },
              {
                key: 'created_at',
                label: intl.formatMessage({
                  id: 'pages.store.field.createdAt',
                  defaultMessage: '创建时间',
                }),
                children: formatDateTime(detail.created_at),
              },
              {
                key: 'updated_at',
                label: intl.formatMessage({
                  id: 'pages.store.field.updatedAt',
                  defaultMessage: '更新时间',
                }),
                children: formatDateTime(detail.updated_at),
              },
            ]}
          />
        ) : (
          !loading &&
          intl.formatMessage({
            id: 'pages.store.notFound',
            defaultMessage: '未找到该店铺',
          })
        )}
      </Card>
    </PageContainer>
  );
};

export default StoreDetailPage;
