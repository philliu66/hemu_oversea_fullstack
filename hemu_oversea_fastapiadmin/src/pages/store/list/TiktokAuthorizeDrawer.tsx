import { App, Button, Drawer, Space } from 'antd';
import React, { useState } from 'react';
import { fetchTiktokAuthorizeUrl } from '@/services/admin/stores';
import { openAuthorizeWindow } from '../openAuthorizeWindow';

export function TiktokAuthorizeDrawer({
  open,
  supplierId,
  onClose,
}: {
  open: boolean;
  supplierId?: number;
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const [submitting, setSubmitting] = useState(false);

  const handleStart = async () => {
    setSubmitting(true);
    try {
      const data = await fetchTiktokAuthorizeUrl(supplierId);
      if (!data.authorize_url) {
        message.error('未获取到授权链接');
        return;
      }
      const popup = openAuthorizeWindow(data.authorize_url);
      if (!popup) {
        message.warning('浏览器拦截了弹窗，请允许后重试');
        return;
      }
      onClose();
    } catch {
      // 错误已由全局拦截器处理
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Drawer
      title="TikTok 店铺授权"
      open={open}
      width={480}
      destroyOnHidden
      maskClosable={false}
      onClose={onClose}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={onClose}>取消</Button>
          <Button
            type="primary"
            loading={submitting}
            onClick={() => void handleStart()}
          >
            开始授权
          </Button>
        </Space>
      }
    >
      <p>
        授权成功后，系统会按 TikTok 返回的店铺自动创建。本地卖家通常是 1
        家，跨境卖家会按国家站点各建一家。不需要填写店铺名称或账号。
      </p>
      <p>请使用卖家账号完成授权。授权窗口关闭后，结果会回到店铺列表。</p>
    </Drawer>
  );
}
