import { useIntl } from '@umijs/max';
import { App, Drawer, Spin } from 'antd';
import React, { useEffect, useState } from 'react';
import { fetchMissionFissionDataDetail } from '@/services/admin/missions';
import type {
  DhProductDetailPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';
import { FissionProductStep } from './FissionProductStep';

function asChangedAttrList(value: unknown): DhProductSelectedAttrPublic[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const result: DhProductSelectedAttrPublic[] = [];
  for (const item of value) {
    if (!item || typeof item !== 'object') {
      continue;
    }
    const raw = item as Record<string, unknown>;
    if (raw.attr_id == null || String(raw.attr_id).trim() === '') {
      continue;
    }
    result.push({
      ...(item as DhProductSelectedAttrPublic),
      attr_id: String(raw.attr_id),
    });
  }
  return result;
}

export function ViewFissionDrawer({
  open,
  missionId,
  dataId,
  onClose,
}: {
  open: boolean;
  missionId: number;
  dataId?: number;
  onClose: () => void;
}) {
  const intl = useIntl();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<DhProductDetailPublic>();
  const [changedKeys, setChangedKeys] = useState<string[]>([]);
  const [changedAttrList, setChangedAttrList] = useState<
    DhProductSelectedAttrPublic[]
  >([]);

  useEffect(() => {
    if (!open || !dataId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setDetail(undefined);
    setChangedKeys([]);
    setChangedAttrList([]);
    void fetchMissionFissionDataDetail({
      id: dataId,
      mission_id: missionId,
    })
      .then((data) => {
        if (cancelled) {
          return;
        }
        const updateJson = data.update_json || {};
        setDetail(data.raw_json ?? undefined);
        setChangedKeys(Object.keys(updateJson));
        setChangedAttrList(asChangedAttrList(updateJson.attr_list));
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          message.error(
            error instanceof Error
              ? error.message
              : intl.formatMessage({
                  id: 'pages.product.detail.loadFailed',
                  defaultMessage: '加载商品详情失败',
                }),
          );
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
  }, [dataId, intl, message, missionId, open]);

  return (
    <Drawer
      title={intl.formatMessage({
        id: 'pages.mission.action.viewChanges',
        defaultMessage: '查看变更',
      })}
      open={open}
      width="80vw"
      destroyOnHidden
      onClose={onClose}
      styles={{ body: { padding: 24 } }}
    >
      <Spin spinning={loading}>
        {detail ? (
          <FissionProductStep
            key={dataId}
            readOnly
            initialDetail={detail}
            changedKeys={changedKeys}
            changedAttrList={changedAttrList}
          />
        ) : null}
      </Spin>
    </Drawer>
  );
}
