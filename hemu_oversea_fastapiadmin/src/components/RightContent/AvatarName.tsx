import { useModel } from '@umijs/max';
import { Tag } from 'antd';
import React from 'react';
import { accountRoleLabel } from '@/utils/accountRoleLabel';

/** 顶栏头像旁：用户名 + 角色标签 */
const AvatarName: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const role = currentUser?.role || currentUser?.access;

  const roleLabel = role ? accountRoleLabel(String(role)) : '';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        maxWidth: 220,
      }}
    >
      <span
        style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {currentUser?.name}
      </span>
      {roleLabel ? (
        <Tag color="blue" style={{ marginInlineEnd: 0, flexShrink: 0 }}>
          {roleLabel}
        </Tag>
      ) : null}
    </span>
  );
};

export default AvatarName;
