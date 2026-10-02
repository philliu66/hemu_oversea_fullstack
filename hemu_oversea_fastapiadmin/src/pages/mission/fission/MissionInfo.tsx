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

const MISSION_STATUS_LABEL: Record<MissionStatus, string> = {
  pending: '未开始',
  running: '进行中',
  finished: '已结束',
  marked_finished: '标记结束',
};

export function MissionStatusTag({ status }: { status: MissionStatus }) {
  return (
    <Tag color={STATUS_COLOR[status]}>
      {MISSION_STATUS_LABEL[status] ?? status}
    </Tag>
  );
}

export function MissionInfo({ mission }: { mission: MissionPublic }) {
  return (
    <Collapse
      defaultActiveKey={['info']}
      items={[
        {
          key: 'info',
          label: '任务信息',
          children: (
            <Descriptions column={2}>
              <Descriptions.Item
                label={'任务标题'}
              >
                {mission.title}
              </Descriptions.Item>
              <Descriptions.Item
                label={'任务状态'}
              >
                <MissionStatusTag status={mission.status} />
              </Descriptions.Item>
              <Descriptions.Item
                label={'创建人'}
              >
                {personLabel(
                  mission.creator_nickname,
                  mission.creator_username,
                )}
              </Descriptions.Item>
              <Descriptions.Item
                label={'任务人员'}
              >
                {personLabel(mission.worker_nickname, mission.worker_username)}
              </Descriptions.Item>
              <Descriptions.Item
                label={'创建时间'}
              >
                {formatDateTime(mission.created_at)}
              </Descriptions.Item>
              <Descriptions.Item
                label={'任务描述'}
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
