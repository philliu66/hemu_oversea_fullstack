import { request } from '@umijs/max';
import { AdminAuthApi, AdminUserApi } from '@/constants/api';
import type {
  ApiResponse,
  AuthLoginResponse,
  UserPublic,
} from '@/types/api';
import { clearTokens, getRefreshToken, setTokens } from '@/utils/authToken';
import { unwrapApiData } from '@/utils/http';
import { mapUserToCurrentUser } from '@/utils/userMapper';

export type CaptchaData = {
  captcha_id: string;
  /** PNG Base64，不含 data: 前缀 */
  image_base64: string;
  expires_in: number;
};

export type AdminLoginParams = {
  username: string;
  /** 明文密码，直接上送 */
  password: string;
  captcha_id: string;
  captcha_code: string;
};

/** GET /api/v1/admin/auth/captcha */
export async function getAdminCaptcha() {
  const res = await request<ApiResponse<CaptchaData>>(AdminAuthApi.CAPTCHA, {
    method: 'GET',
  });
  const data = unwrapApiData<CaptchaData>(res);
  if (!data) {
    throw new Error('获取验证码失败');
  }
  return data;
}

/**
 * POST /api/v1/admin/auth/login
 * body: username + 明文 password + captcha_id + captcha_code
 * data: access_token + refresh_token + user
 */
export async function adminLogin(body: AdminLoginParams) {
  const res = await request<ApiResponse<AuthLoginResponse>>(AdminAuthApi.LOGIN, {
    method: 'POST',
    data: {
      username: body.username,
      password: body.password,
      captcha_id: body.captcha_id,
      captcha_code: body.captcha_code,
    },
  });
  const data = unwrapApiData<AuthLoginResponse>(res);
  if (!data?.access_token || !data.refresh_token || !data.user) {
    throw new Error('登录失败');
  }
  setTokens(data.access_token, data.refresh_token);
  return {
    ...data,
    currentUser: mapUserToCurrentUser(data.user),
  };
}

/** GET /api/v1/admin/users/me —— 返回完整 UserPublic */
export async function fetchAdminMe(options?: { skipErrorHandler?: boolean }) {
  const res = await request<ApiResponse<UserPublic> | UserPublic>(
    AdminUserApi.ME,
    {
      method: 'GET',
      ...(options || {}),
    },
  );
  // 兼容：完整信封 或 已解包的 data
  const user = isUserPublic(res)
    ? res
    : unwrapApiData<UserPublic>(res);
  if (!user?.id || !user.username) {
    throw new Error('获取用户信息失败');
  }
  return user;
}

function isUserPublic(value: unknown): value is UserPublic {
  return (
    !!value &&
    typeof value === 'object' &&
    'id' in value &&
    'username' in value &&
    !('code' in value && 'message' in value && 'data' in value)
  );
}

/** GET /api/v1/admin/users/me —— 映射为布局用 currentUser */
export async function getAdminCurrentUser(options?: {
  skipErrorHandler?: boolean;
}) {
  const user = await fetchAdminMe(options);
  return mapUserToCurrentUser(user);
}

/** POST /api/v1/admin/auth/password —— old/new 均为明文 */
export async function adminChangePassword(body: {
  oldPassword: string;
  newPassword: string;
}) {
  await request<ApiResponse<Record<string, never>>>(AdminAuthApi.PASSWORD, {
    method: 'POST',
    data: {
      old_password: body.oldPassword,
      new_password: body.newPassword,
    },
  });
}

/** POST /api/v1/admin/auth/logout */
export async function adminLogout() {
  const refresh_token = getRefreshToken();
  try {
    if (refresh_token) {
      await request<ApiResponse<Record<string, never>>>(AdminAuthApi.LOGOUT, {
        method: 'POST',
        data: { refresh_token },
        skipErrorHandler: true,
      });
    }
  } finally {
    clearTokens();
  }
}
