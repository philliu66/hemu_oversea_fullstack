import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, useIntl, useParams } from '@umijs/max';
import { Button, Card, Spin } from 'antd';
import React, { useEffect, useState } from 'react';
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
  const intl = useIntl();
  const { id } = useParams<{ id: string }>();
  const missionId = parseMissionId(id);
  const [mission, setMission] = useState<MissionPublic>();
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);

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

  const ended =
    mission?.status === 'marked_finished' || mission?.status === 'finished';

  const logColumns: ProColumns<MissionLogPublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.operator',
        defaultMessage: '执行人员',
      }),
      dataIndex: 'operator_nickname',
      render: (_, record) =>
        personLabel(record.operator_nickname, record.operator_username),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.startedAt',
        defaultMessage: '开始时间',
      }),
      dataIndex: 'started_at',
      render: (_, record) => formatDateTime(record.started_at),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.endedAt',
        defaultMessage: '结束时间',
      }),
      dataIndex: 'ended_at',
      render: (_, record) => formatDateTime(record.ended_at),
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.successCount',
        defaultMessage: '成功数量',
      }),
      dataIndex: 'success_count',
    },
    {
      title: intl.formatMessage({
        id: 'pages.mission.field.failCount',
        defaultMessage: '失败数量',
      }),
      dataIndex: 'fail_count',
    },
  ];

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
      title={
        mission?.title ||
        intl.formatMessage({
          id: 'pages.mission.detail.title',
          defaultMessage: '任务详情',
        })
      }
      onBack={() => history.push(MISSION_FISSION_PATH)}
      extra={
        <Button
          type="primary"
          disabled={!mission || ended}
          loading={executing}
          onClick={async () => {
            setExecuting(true);
            try {
              await executeMission(missionId);
            } catch {
              // 占位接口的「功能待补充」由全局错误提示展示
            } finally {
              setExecuting(false);
            }
          }}
        >
          {intl.formatMessage({
            id: 'pages.mission.action.execute',
            defaultMessage: '执行任务',
          })}
        </Button>
      }
    >
      <Spin spinning={loading}>
        {mission ? <MissionInfo mission={mission} /> : null}
        <div style={{ marginTop: 16 }}>
          <FissionDataTable missionId={missionId} />
        </div>
        <div style={{ marginTop: 16 }}>
          <ProTable<MissionLogPublic>
            rowKey="id"
            search={false}
            headerTitle={intl.formatMessage({
              id: 'pages.mission.detail.logs',
              defaultMessage: '执行日志',
            })}
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
      </Spin>
    </PageContainer>
  );
};

export default MissionFissionDetailPage;
