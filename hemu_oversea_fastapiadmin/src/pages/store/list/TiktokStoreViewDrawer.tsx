import { Button, Drawer, Form, Input, Space, Spin, Tag } from 'antd';
import React, { useEffect, useState } from 'react';
import {
  STORE_OAUTH_STATUS,
  STORE_OAUTH_STATUS_COLOR,
  STORE_OAUTH_STATUS_LABEL,
  type StoreOauthStatusValue,
} from '@/constants/store';
import { fetchStoreDetail } from '@/services/admin/stores';
import type { StoreDetailPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';

function isOauthStatus(value: number): value is StoreOauthStatusValue {
  return (
    value === STORE_OAUTH_STATUS.UNAUTHORIZED ||
    value === STORE_OAUTH_STATUS.AUTHORIZED ||
    value === STORE_OAUTH_STATUS.EXPIRED
  );
}

function sellerTypeLabel(value?: string | null) {
  if (value === 'LOCAL') {
    return '本地';
  }
  if (value === 'CROSS_BORDER') {
    return '跨境';
  }
  return value || '-';
}

export function TiktokStoreViewDrawer({
  open,
  storeId,
  onClose,
}: {
  open: boolean;
  storeId?: number;
  onClose: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<StoreDetailPublic>();

  useEffect(() => {
    if (!open || !storeId) {
      setDetail(undefined);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetchStoreDetail(storeId)
      .then((data) => {
        if (!cancelled) {
          setDetail(data);
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
  }, [open, storeId]);

  const oauthStatus = detail?.oauth_status;

  return (
    <Drawer
      title="查看 TikTok 店铺"
      open={open}
      width={480}
      destroyOnHidden
      maskClosable={false}
      onClose={onClose}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={onClose}>关闭</Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Form layout="vertical">
          <Form.Item label="店铺名称">
            <Input disabled value={detail?.name || '-'} />
          </Form.Item>
          <Form.Item label="店铺代码">
            <Input
              disabled
              value={detail?.platform_shop_code || detail?.identifier || '-'}
            />
          </Form.Item>
          <Form.Item label="区域">
            <Input disabled value={detail?.platform_region || '-'} />
          </Form.Item>
          <Form.Item label="卖家类型">
            <Input
              disabled
              value={sellerTypeLabel(detail?.platform_seller_type)}
            />
          </Form.Item>
          <Form.Item label="授权状态">
            {oauthStatus !== undefined && isOauthStatus(oauthStatus) ? (
              <Tag color={STORE_OAUTH_STATUS_COLOR[oauthStatus]}>
                {STORE_OAUTH_STATUS_LABEL[oauthStatus]}
              </Tag>
            ) : (
              '-'
            )}
          </Form.Item>
          <Form.Item label="授权到期">
            <Input
              disabled
              value={formatDateTime(detail?.refresh_token_expires_at) || '-'}
            />
          </Form.Item>
        </Form>
      </Spin>
    </Drawer>
  );
}
