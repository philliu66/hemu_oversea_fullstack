import { Button, Drawer, Form, Select, Space } from 'antd';
import React, { useEffect, useState } from 'react';
import {
  STORE_TYPE_LABEL,
  STORE_TYPES,
  type StoreTypeValue,
} from '@/constants/store';

export function StoreTypePickDrawer({
  open,
  onClose,
  onPick,
}: {
  open: boolean;
  onClose: () => void;
  onPick: (storeType: StoreTypeValue) => void;
}) {
  const [storeType, setStoreType] = useState<StoreTypeValue>();

  useEffect(() => {
    if (!open) {
      setStoreType(undefined);
    }
  }, [open]);

  return (
    <Drawer
      title="新建店铺"
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
            disabled={!storeType}
            onClick={() => {
              if (storeType) {
                onPick(storeType);
              }
            }}
          >
            下一步
          </Button>
        </Space>
      }
    >
      <Form layout="vertical">
        <Form.Item label="店铺类型" required>
          <Select
            placeholder="请选择店铺类型"
            value={storeType}
            options={STORE_TYPES.map((type) => ({
              label: STORE_TYPE_LABEL[type],
              value: type,
            }))}
            onChange={(value: StoreTypeValue) => setStoreType(value)}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
