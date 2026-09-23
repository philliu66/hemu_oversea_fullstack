import { useIntl } from '@umijs/max';
import { Collapse, Descriptions, Tag } from 'antd';
import React from 'react';
import type { MissionPublic, MissionStatus } from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import { personLabel } from './utils';

const STATUS_COLOR: Record<MissionStatus, string> = {
  pending: 'default',
  running: 'processing',
  finished: 'success',
  marked_finished: 'warning',
};

export function MissionStatusTag({ status }: { status: MissionStatus }) {
  const intl = useIntl();
  const labelKey = {
    pending: 'pages.mission.status.pending',
    running: 'pages.mission.status.running',
    finished: 'pages.mission.status.finished',
    marked_finished: 'pages.mission.status.markedFinished',
  }[status];
  return (
    <Tag color={STATUS_COLOR[status]}>
      {intl.formatMessage({
        id: labelKey,
        defaultMessage: status,
      })}
    </Tag>
  );
}

export function MissionInfo({ mission }: { mission: MissionPublic }) {
  const intl = useIntl();
  return (
    <Collapse
      defaultActiveKey={['info']}
      items={[
        {
          key: 'info',
          label: intl.formatMessage({
            id: 'pages.mission.info.section',
            defaultMessage: '任务信息',
          }),
          children: (
            <Descriptions column={2}>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.mission.field.title',
                  defaultMessage: '任务标题',
                })}
              >
                {mission.title}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.mission.field.status',
                  defaultMessage: '任务状态',
                })}
              >
                <MissionStatusTag status={mission.status} />
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.mission.field.creator',
                  defaultMessage: '创建人',
                })}
              >
                {personLabel(
                  mission.creator_nickname,
                  mission.creator_username,
                )}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.mission.field.worker',
                  defaultMessage: '任务人员',
                })}
              >
                {personLabel(mission.worker_nickname, mission.worker_username)}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.mission.field.createdAt',
                  defaultMessage: '创建时间',
                })}
              >
                {formatDateTime(mission.created_at)}
              </Descriptions.Item>
              <Descriptions.Item
                label={intl.formatMessage({
                  id: 'pages.mission.field.description',
                  defaultMessage: '任务描述',
                })}
              >
                {mission.description || '-'}
              </Descriptions.Item>
            </Descriptions>
          ),
        },
      ]}
    />
  );
}
