import { useSearchParams } from '@umijs/max';
import { Result } from 'antd';
import React, { useEffect, useMemo } from 'react';
import {
  STORE_OAUTH_RESULT_MESSAGE_TYPE,
  type StoreOauthResultMessage,
} from '@/constants/store';

type CallbackStatus = 'success' | 'fail' | 'unknown';

function resolveOpener(): Window | null {
  if (window.opener && !window.opener.closed) {
    return window.opener;
  }
  try {
    if (
      window.parent &&
      window.parent !== window &&
      window.parent.opener &&
      !window.parent.opener.closed
    ) {
      return window.parent.opener;
    }
  } catch {
    // cross-origin parent
  }
  try {
    if (window.top?.opener && !window.top.opener.closed) {
      return window.top.opener;
    }
  } catch {
    // cross-origin top
  }
  return null;
}

function parseStoreId(raw: string | null): number | undefined {
  if (!raw) return undefined;
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

const CallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  const status = useMemo<CallbackStatus>(() => {
    const raw = (searchParams.get('status') || '').toLowerCase();
    if (raw === 'success') return 'success';
    if (raw === 'fail' || raw === 'failed' || raw === 'error') return 'fail';
    return 'unknown';
  }, [searchParams]);

  const msg = useMemo(() => {
    return (searchParams.get('msg') || '').trim();
  }, [searchParams]);

  const storeId = useMemo(() => {
    return parseStoreId(searchParams.get('store_id'));
  }, [searchParams]);

  useEffect(() => {
    const opener = resolveOpener();
    if (!opener) {
      return;
    }
    const payload: StoreOauthResultMessage = {
      type: STORE_OAUTH_RESULT_MESSAGE_TYPE,
      status: status === 'success' ? 'success' : 'fail',
      msg,
      ...(storeId !== undefined ? { store_id: storeId } : {}),
    };
    try {
      opener.postMessage(payload, window.location.origin);
    } catch {
      // opener 不可达时忽略
    }
  }, [msg, status, storeId]);

  useEffect(() => {
    if (status !== 'success') {
      return;
    }
    const timer = window.setTimeout(() => {
      window.close();
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [status]);

  const resultStatus = status === 'success' ? 'success' : 'error';
  const title =
    status === 'success'
      ? '授权成功'
      : status === 'fail'
        ? '授权失败'
        : '授权结果未知';

  const subTitle =
    msg ||
    (status === 'success'
      ? '店铺授权已完成，窗口将在 3 秒后自动关闭。'
      : status === 'fail'
        ? '授权未完成，请关闭本窗口后重试。'
        : '未识别到有效的授权结果参数。');

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: 'var(--ant-color-bg-layout, #f5f5f5)',
      }}
    >
      <Result status={resultStatus} title={title} subTitle={subTitle} />
    </div>
  );
};

export default CallbackPage;
