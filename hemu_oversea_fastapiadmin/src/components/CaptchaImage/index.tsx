import { ReloadOutlined } from '@ant-design/icons';
import { Spin } from 'antd';
import { createStyles } from 'antd-style';
import React from 'react';

export type CaptchaImageProps = {
  /** PNG Base64，可不含 data: 前缀 */
  imageBase64?: string;
  width?: number;
  height?: number;
  loading?: boolean;
  onRefresh?: () => void;
};

const useStyles = createStyles(({ token }) => ({
  wrap: {
    position: 'relative',
    flex: 'none',
    overflow: 'hidden',
    padding: 0,
    lineHeight: 0,
    cursor: 'pointer',
    userSelect: 'none',
    border: `1px solid ${token.colorBorder}`,
    borderRadius: token.borderRadius,
    background: token.colorFillTertiary,
  },
  image: {
    display: 'block',
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  placeholder: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: token.colorTextSecondary,
    fontSize: token.fontSizeSM,
    background: token.colorFillTertiary,
  },
  refresh: {
    position: 'absolute',
    right: 4,
    bottom: 4,
    color: token.colorTextTertiary,
    fontSize: 12,
    pointerEvents: 'none',
  },
}));

function toDataUrl(imageBase64: string): string {
  if (imageBase64.startsWith('data:')) {
    return imageBase64;
  }
  return `data:image/png;base64,${imageBase64}`;
}

const CaptchaImage: React.FC<CaptchaImageProps> = ({
  imageBase64,
  width = 120,
  height = 40,
  loading = false,
  onRefresh,
}) => {
  const { styles } = useStyles();

  return (
    <Spin spinning={loading} size="small">
      <button
        type="button"
        className={styles.wrap}
        style={{ width, height }}
        title="点击刷新验证码"
        onClick={onRefresh}
      >
        {imageBase64 ? (
          <img
            className={styles.image}
            src={toDataUrl(imageBase64)}
            alt="图形验证码"
            draggable={false}
          />
        ) : (
          <span className={styles.placeholder}>点击获取</span>
        )}
        <ReloadOutlined className={styles.refresh} />
      </button>
    </Spin>
  );
};

export default CaptchaImage;
