import { App, Button, Drawer, Space, Spin } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import type { ProductEditorHandle } from '@/pages/product/detail/ProductEditor';
import { fetchDhProductDetail } from '@/services/admin/products';
import {
  fetchMissionFissionDataDetail,
  updateMissionFissionData,
} from '@/services/admin/missions';
import type { DhProductDetailPublic } from '@/types/api';
import { FissionProductStep } from './FissionProductStep';
import { buildFissionUpdateData } from './fissionUpdate';

function looksLikeEditorDetail(
  value: DhProductDetailPublic | null | undefined,
): value is DhProductDetailPublic {
  return Boolean(value && typeof value === 'object' && 'id' in value);
}

export function EditFissionDrawer({
  open,
  missionId,
  dataId,
  onClose,
  onSaved,
}: {
  open: boolean;
  missionId: number;
  dataId?: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rawDetail, setRawDetail] = useState<DhProductDetailPublic>();
  const [seedDetail, setSeedDetail] = useState<DhProductDetailPublic>();
  const editorRef = useRef<ProductEditorHandle>(null);

  useEffect(() => {
    if (!open || !dataId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setRawDetail(undefined);
    setSeedDetail(undefined);
    void (async () => {
      try {
        const data = await fetchMissionFissionDataDetail({
          id: dataId,
          mission_id: missionId,
        });
        if (cancelled) {
          return;
        }
        if (data.fission_status === 'success') {
          message.warning('裂变成功的数据不能编辑');
          onClose();
          return;
        }
        if (!data.raw_json) {
          message.error('任务数据正文缺失，无法编辑');
          onClose();
          return;
        }
        let seed = looksLikeEditorDetail(data.seed_json)
          ? data.seed_json
          : undefined;
        if (!seed && data.seed_product_id) {
          try {
            seed = await fetchDhProductDetail(data.seed_product_id);
          } catch {
            // 回退失败时保存阶段再报错
          }
        }
        if (cancelled) {
          return;
        }
        setRawDetail(data.raw_json);
        setSeedDetail(seed);
      } catch (error: unknown) {
        if (!cancelled) {
          message.error(
            error instanceof Error ? error.message : '加载任务数据失败',
          );
          onClose();
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [dataId, message, missionId, onClose, open]);

  const handleSave = async () => {
    if (!dataId) {
      return;
    }
    if (!editorRef.current?.isReady()) {
      message.warning('商品信息还在加载，请稍后再确认');
      return;
    }
    const current = editorRef.current.getSnapshot();
    if (!current) {
      message.warning('商品信息还在加载，请稍后再确认');
      return;
    }
    if (!seedDetail) {
      message.error('缺少最初种子详情，无法计算变更');
      return;
    }
    const baseline = seedDetail;
    const updateJson = buildFissionUpdateData(baseline, current);
    setSubmitting(true);
    try {
      await updateMissionFissionData({
        id: dataId,
        mission_id: missionId,
        update_json: updateJson,
        raw_json: current,
      });
      message.success('已保存');
      onSaved();
    } catch {
      // 错误已由全局拦截器处理
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Drawer
      title={'编辑任务数据'}
      open={open}
      width="80vw"
      destroyOnHidden
      onClose={onClose}
      styles={{
        body: {
          padding: 24,
          overflow: 'auto',
        },
      }}
      footer={
        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onClose}>{'取消'}</Button>
            <Button type="primary" loading={submitting} onClick={handleSave}>
              {'保存'}
            </Button>
          </Space>
        </div>
      }
    >
      <Spin spinning={loading}>
        {rawDetail ? (
          <FissionProductStep
            key={dataId}
            ref={editorRef}
            initialDetail={rawDetail}
          />
        ) : null}
      </Spin>
    </Drawer>
  );
}
