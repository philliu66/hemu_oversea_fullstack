import { PageContainer } from '@ant-design/pro-components';
import { history, useAccess, useParams } from '@umijs/max';
import { App, Card, Spin } from 'antd';
import React, { useEffect, useState } from 'react';
import { fetchMissionDetail } from '@/services/admin/missions';
import type { MissionPublic } from '@/types/api';
import { MissionInfo } from '../fission/MissionInfo';
import { HotsaleDataTable } from './HotsaleDataTable';
import { MISSION_HOTSALE_PATH, parseMissionId } from './utils';

/** 热卖采集 · 设置任务数据（无手动添加；「开始采集」对接浏览器扩展） */
const MissionHotsaleDataPage: React.FC = () => {
  const access = useAccess();
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const missionId = parseMissionId(id);
  const [mission, setMission] = useState<MissionPublic>();
  const [loading, setLoading] = useState(true);
  const canViewData =
    access.can('mission.hotsale.data') || access.canPlatform;
  const canWriteData = access.canWriteSupplierData;

  useEffect(() => {
    if (!canViewData) {
      message.warning('无查看任务数据权限');
      history.replace(MISSION_HOTSALE_PATH);
    }
  }, [canViewData, message]);

  useEffect(() => {
    if (!missionId || !canViewData) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetchMissionDetail(missionId)
      .then((detail) => {
        if (!cancelled) {
          setMission(detail);
        }
      })
      .catch(() => {
        if (!cancelled) {
          history.replace(MISSION_HOTSALE_PATH);
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
  }, [canViewData, missionId]);

  if (!missionId) {
    return (
      <PageContainer onBack={() => history.push(MISSION_HOTSALE_PATH)}>
        <Card>{'任务 ID 无效'}</Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={canWriteData ? '设置任务数据' : '查看任务数据'}
      onBack={() => history.push(MISSION_HOTSALE_PATH)}
    >
      <Spin spinning={loading}>
        {mission ? <MissionInfo mission={mission} /> : null}
        <div style={{ marginTop: 16 }}>
          <HotsaleDataTable
            missionId={missionId}
            supplierId={mission?.supplier_id}
            editable={canWriteData}
          />
        </div>
      </Spin>
    </PageContainer>
  );
};

export default MissionHotsaleDataPage;
