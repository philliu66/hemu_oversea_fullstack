import { PageContainer } from '@ant-design/pro-components';
import { history, useAccess, useIntl, useParams } from '@umijs/max';
import { App, Card, Spin } from 'antd';
import React, { useEffect, useState } from 'react';
import { fetchMissionDetail } from '@/services/admin/missions';
import type { MissionPublic } from '@/types/api';
import { FissionDataTable } from './FissionDataTable';
import { MissionInfo } from './MissionInfo';
import { MISSION_FISSION_PATH, parseMissionId } from './utils';

const MissionFissionDataPage: React.FC = () => {
  const intl = useIntl();
  const access = useAccess();
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const missionId = parseMissionId(id);
  const [mission, setMission] = useState<MissionPublic>();
  const [loading, setLoading] = useState(true);
  const canSetData = access.can('mission.fission.data');

  useEffect(() => {
    if (!canSetData) {
      message.warning(
        intl.formatMessage({
          id: 'pages.mission.forbiddenData',
          defaultMessage: '无设置任务数据权限',
        }),
      );
      history.replace(MISSION_FISSION_PATH);
    }
  }, [canSetData, intl, message]);

  useEffect(() => {
    if (!missionId || !canSetData) {
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
          history.replace(MISSION_FISSION_PATH);
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
  }, [canSetData, missionId]);

  if (!missionId) {
    return (
      <PageContainer onBack={() => history.push(MISSION_FISSION_PATH)}>
        <Card>
          {intl.formatMessage({
            id: 'pages.mission.invalidId',
            defaultMessage: '任务 ID 无效',
          })}
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={intl.formatMessage({
        id: 'pages.mission.data.title',
        defaultMessage: '设置任务数据',
      })}
      onBack={() => history.push(MISSION_FISSION_PATH)}
    >
      <Spin spinning={loading}>
        {mission ? <MissionInfo mission={mission} /> : null}
        <div style={{ marginTop: 16 }}>
          <FissionDataTable missionId={missionId} editable />
        </div>
      </Spin>
    </PageContainer>
  );
};

export default MissionFissionDataPage;
