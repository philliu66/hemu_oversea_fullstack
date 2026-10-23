import { PageContainer } from '@ant-design/pro-components';
import { history, useParams } from '@umijs/max';
import { Card, Spin } from 'antd';
import React, { useEffect, useState } from 'react';
import { fetchMissionDetail } from '@/services/admin/missions';
import type { MissionPublic } from '@/types/api';
import { MissionInfo } from '../fission/MissionInfo';
import { MISSION_HOTSALE_PATH, parseMissionId } from './utils';

/** 热卖采集 · 任务详情（类型不展示；执行/日志后续对接） */
const MissionHotsaleDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const missionId = parseMissionId(id);
  const [mission, setMission] = useState<MissionPublic>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!missionId) {
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
  }, [missionId]);

  if (!missionId) {
    return (
      <PageContainer onBack={() => history.push(MISSION_HOTSALE_PATH)}>
        <Card>{'任务 ID 无效'}</Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title="任务详情"
      onBack={() => history.push(MISSION_HOTSALE_PATH)}
    >
      <Spin spinning={loading}>
        {mission ? <MissionInfo mission={mission} /> : null}
      </Spin>
    </PageContainer>
  );
};

export default MissionHotsaleDetailPage;
