import { PageContainer } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { createStyles } from 'antd-style';
import React from 'react';
import { buildSystemTitle } from '@/constants/brand';

const useStyles = createStyles(({ token, css }) => ({
  page: css`
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: calc(100vh - 180px);
  `,
  hero: css`
    @keyframes welcomeEnter {
      from {
        opacity: 0;
        transform: translateY(28px) scale(0.97);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    text-align: center;
    font-size: 36px;
    font-weight: 600;
    line-height: 1.4;
    color: ${token.colorText};
    opacity: 0;
    animation: welcomeEnter 0.75s cubic-bezier(0.22, 1, 0.36, 1) forwards;

    @media (max-width: 768px) {
      font-size: 28px;
    }
  `,
  title: css`
    background: linear-gradient(135deg, #1677ff 0%, #722ed1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  `,
}));

const Welcome: React.FC = () => {
  const { styles } = useStyles();
  const { initialState } = useModel('@@initialState');
  const title = buildSystemTitle(initialState?.currentUser?.supplier_name);

  return (
    <PageContainer title={false} pageHeaderRender={false}>
      <div className={styles.page}>
        <div className={styles.hero}>
          欢迎使用 <span className={styles.title}>{title}</span>
        </div>
      </div>
    </PageContainer>
  );
};

export default Welcome;
