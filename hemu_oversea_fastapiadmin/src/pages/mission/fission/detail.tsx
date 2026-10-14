import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useAccess, useParams } from '@umijs/max';
import { App, Button, Card, Spin } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  executeMission,
  fetchMissionDetail,
  fetchMissionLogList,
} from '@/services/admin/missions';
import type { MissionLogPublic, MissionPublic } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { FissionDataTable } from './FissionDataTable';
import { MissionInfo } from './MissionInfo';
import { MISSION_FISSION_PATH, parseMissionId, personLabel } from './utils';

const MissionFissionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const missionId = parseMissionId(id);
  const access = useAccess();
  const { message } = App.useApp();
  const logActionRef = useRef<ActionType | null>(null);
  const [mission, setMission] = useState<MissionPublic>();
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const canViewLogs = access.can('mission.logs');

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
  }, [missionId]);

  const canExecute =
    !!mission &&
    mission.status !== 'marked_finished' &&
    mission.status !== 'running';

  const logColumns: ProColumns<MissionLogPublic>[] = [
    {
      title: '执行人员',
      dataIndex: 'operator_nickname',
      render: (_, record) =>
        personLabel(record.operator_nickname, record.operator_username),
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      render: (_, record) => formatDateTime(record.started_at),
    },
    {
      title: '结束时间',
      dataIndex: 'ended_at',
      render: (_, record) => formatDateTime(record.ended_at),
    },
    {
      title: '成功数量',
      dataIndex: 'success_count',
    },
    {
      title: '失败数量',
      dataIndex: 'fail_count',
    },
  ];

  if (!missionId) {
    return (
      <PageContainer onBack={() => history.push(MISSION_FISSION_PATH)}>
        <Card>
          {'任务 ID 无效'}
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={
        mission?.title ||
        '任务详情'
      }
      onBack={() => history.push(MISSION_FISSION_PATH)}
      extra={
        <Button
          type="primary"
          disabled={!canExecute}
          loading={executing}
          onClick={async () => {
            setExecuting(true);
            try {
              const result = await executeMission(missionId);
              message.success(`已提交执行，共 ${result.queued_count} 条`);
              const detail = await fetchMissionDetail(missionId);
              setMission(detail);
              if (canViewLogs) {
                logActionRef.current?.reload();
              }
            } catch {
              // 业务错误由全局错误提示展示
            } finally {
              setExecuting(false);
            }
          }}
        >
          {'执行任务'}
        </Button>
      }
    >
      <Spin spinning={loading}>
        {mission ? <MissionInfo mission={mission} /> : null}
        <div style={{ marginTop: 16 }}>
          <FissionDataTable missionId={missionId} />
        </div>
        {canViewLogs ? (
          <div style={{ marginTop: 16 }}>
            <ProTable<MissionLogPublic>
              actionRef={logActionRef}
              rowKey="id"
              search={false}
              headerTitle={'执行日志'}
              pagination={{
                defaultPageSize: PAGE_SIZE_DEFAULT,
                showSizeChanger: true,
              }}
              request={async (params) => {
                const result = await fetchMissionLogList({
                  mission_id: missionId,
                  page: params.current,
                  page_size: params.pageSize,
                });
                return {
                  data: result.items,
                  success: true,
                  total: result.total,
                };
              }}
              columns={logColumns}
            />
          </div>
        ) : null}
      </Spin>
    </PageContainer>
  );
};

export default MissionFissionDetailPage;
