import { useModel } from '@umijs/max';
import { createStyles } from 'antd-style';
import React from 'react';
import { buildSystemTitle } from '@/constants/brand';

const useStyles = createStyles(({ token, css }) => ({
  footer: css`
    padding: 16px 24px;
    text-align: center;
    color: ${token.colorTextDescription};
    font-size: ${token.fontSizeSM}px;
    line-height: ${token.lineHeight};
    background: transparent;
  `,
}));

const Footer: React.FC = () => {
  const { styles } = useStyles();
  const { initialState } = useModel('@@initialState');
  const year = new Date().getFullYear();
  const title = buildSystemTitle(initialState?.currentUser?.supplier_name);

  return (
    <div className={styles.footer}>
      {title} &copy; {year}
    </div>
  );
};

export default Footer;
