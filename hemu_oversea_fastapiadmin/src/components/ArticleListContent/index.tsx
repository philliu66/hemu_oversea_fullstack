import { Avatar } from 'antd';
import React from 'react';
import { formatDateTime } from '@/utils/datetime';
import useStyles from './index.style';

export type ArticleListContentProps = {
  data: {
    content?: React.ReactNode;
    updatedAt?: number;
    avatar?: string;
    owner?: string;
    href?: string;
  };
};

const ArticleListContent: React.FC<ArticleListContentProps> = ({
  data: { content, updatedAt, avatar, owner, href },
}) => {
  const { styles } = useStyles();
  return (
    <div>
      <div className={styles.description}>{content}</div>
      <div className={styles.extra}>
        <Avatar src={avatar} size="small" />
        <a href={href}>{owner}</a> 发布在 <a href={href}>{href}</a>
        <em>{formatDateTime(updatedAt, 'YYYY-MM-DD HH:mm')}</em>
      </div>
    </div>
  );
};

export default ArticleListContent;
