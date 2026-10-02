import { LockOutlined, SafetyOutlined, UserOutlined } from '@ant-design/icons';
import {
  LoginForm,
  type ProFormInstance,
  ProFormText,
} from '@ant-design/pro-components';
import { Helmet, useModel } from '@umijs/max';
import { App } from 'antd';
import { createStyles } from 'antd-style';
import React, {
  startTransition,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import CaptchaImage from '@/components/CaptchaImage';
import { adminLogin, getAdminCaptcha } from '@/services/admin/auth';
import Settings from '../../../../config/defaultSettings';

/**
 * Validate redirect URL to prevent open redirect attacks.
 * Only allow same-origin relative paths starting with '/'.
 */
const getSafeRedirectUrl = (redirect: string | null): string => {
  if (!redirect?.startsWith('/')) return '/';

  if (redirect.startsWith('//')) return '/';

  try {
    const parsed = new URL(redirect, window.location.origin);
    if (parsed.origin !== window.location.origin) return '/';
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return '/';
  }
};

const useStyles = createStyles(({ token }) => {
  return {
    container: {
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      overflow: 'auto',
      backgroundImage:
        "url('https://mdn.alipayobjects.com/yuyan_qk0oxh/afts/img/V-_oS6r-i7wAAAAAAAAAAAAAFl94AQBr')",
      backgroundSize: '100% 100%',
    },
    captchaRow: {
      display: 'flex',
      gap: 8,
      alignItems: 'flex-start',
    },
    captchaInput: {
      flex: 1,
    },
  };
});

type LoginFormValues = {
  username: string;
  password: string;
  captcha_id?: string;
  captcha_code: string;
};

const Login: React.FC = () => {
  const [captchaImage, setCaptchaImage] = useState('');
  const [captchaLoading, setCaptchaLoading] = useState(false);
  const formRef = useRef<ProFormInstance>(undefined);
  const { setInitialState } = useModel('@@initialState');
  const { styles } = useStyles();
  const { message } = App.useApp();
  const fetchCaptcha = useCallback(async () => {
    setCaptchaLoading(true);
    try {
      const data = await getAdminCaptcha();
      setCaptchaImage(data.image_base64);
      formRef.current?.setFieldsValue({
        captcha_id: data.captcha_id,
        captcha_code: undefined,
      });
    } catch {
      setCaptchaImage('');
      formRef.current?.setFieldsValue({
        captcha_id: undefined,
        captcha_code: undefined,
      });
      message.error(
        '获取验证码失败，请点击图片重试',
      );
    } finally {
      setCaptchaLoading(false);
    }
  }, [message]);

  useEffect(() => {
    fetchCaptcha();
  }, [fetchCaptcha]);

  const handleSubmit = async (values: LoginFormValues) => {
    if (!values.captcha_id) {
      message.error(
        '请先获取验证码',
      );
      fetchCaptcha();
      return;
    }

    try {
      const result = await adminLogin({
        username: values.username,
        password: values.password,
        captcha_id: values.captcha_id,
        captcha_code: values.captcha_code,
      });
      // 登录成功：用户信息写入全局 initialState
      startTransition(() => {
        setInitialState((s) => ({
          ...s,
          currentUser: result.currentUser,
        }));
      });
      message.success(
        '登录成功！',
      );
      const urlParams = new URL(window.location.href).searchParams;
      window.location.href = getSafeRedirectUrl(urlParams.get('redirect'));
    } catch {
      // 业务错误提示由全局响应拦截器处理
      fetchCaptcha();
    }
  };

  return (
    <div className={styles.container}>
      <Helmet>
        <title>
          {'登录页'}
          {Settings.title && ` - ${Settings.title}`}
        </title>
      </Helmet>
      <div
        style={{
          flex: '1',
          padding: '32px 0',
        }}
      >
        <LoginForm
          formRef={formRef}
          contentStyle={{
            minWidth: 280,
            maxWidth: '75vw',
            paddingTop: 64,
          }}
          logo={<img alt="logo" src="/logo.png" />}
          title={Settings.title}
          subTitle={false}
          onFinish={async (values) => {
            await handleSubmit(values as LoginFormValues);
          }}
        >
          <ProFormText
            name="username"
            formItemProps={{
              style: {
                marginTop: 24,
              },
            }}
            fieldProps={{
              size: 'large',
              prefix: <UserOutlined />,
            }}
            placeholder={'请输入账号'}
            rules={[
              {
                required: true,
                message: '请输入账号',
              },
            ]}
          />
          <ProFormText.Password
            name="password"
            fieldProps={{
              size: 'large',
              prefix: <LockOutlined />,
            }}
            placeholder={'请输入密码'}
            rules={[
              {
                required: true,
                message: '请输入密码',
              },
            ]}
          />
          <ProFormText name="captcha_id" hidden />
          <div className={styles.captchaRow}>
            <div className={styles.captchaInput}>
              <ProFormText
                name="captcha_code"
                fieldProps={{
                  size: 'large',
                  prefix: <SafetyOutlined />,
                  maxLength: 8,
                }}
                placeholder={'请输入验证码'}
                rules={[
                  {
                    required: true,
                    message: '请输入验证码！',
                  },
                ]}
              />
            </div>
            <CaptchaImage
              imageBase64={captchaImage}
              loading={captchaLoading}
              onRefresh={fetchCaptcha}
            />
          </div>
        </LoginForm>
      </div>
    </div>
  );
};

export default Login;
