import { message } from 'antd';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { errorConfig } from './requestErrorConfig';

const {
  mockRequest,
  mockTryRefreshTokens,
  mockClearTokens,
  mockReplace,
} = vi.hoisted(() => ({
  mockRequest: vi.fn(),
  mockTryRefreshTokens: vi.fn(),
  mockClearTokens: vi.fn(),
  mockReplace: vi.fn(),
}));

vi.mock('antd', () => ({
  message: {
    warning: vi.fn(),
    error: vi.fn(),
  },
  notification: {
    open: vi.fn(),
  },
}));

vi.mock('@umijs/max', () => ({
  history: {
    replace: mockReplace,
  },
  request: (...args: unknown[]) => mockRequest(...args),
}));

vi.mock('@/utils/authToken', () => ({
  clearTokens: (...args: unknown[]) => mockClearTokens(...args),
  getAccessToken: vi.fn(() => 'test-token'),
}));

vi.mock('@/utils/authRefresh', () => ({
  tryRefreshTokens: (...args: unknown[]) => mockTryRefreshTokens(...args),
}));

describe('requestErrorConfig', () => {
  // biome-ignore lint/style/noNonNullAssertion: config handlers are always defined
  const errorThrower = errorConfig.errorConfig!.errorThrower!;
  // biome-ignore lint/style/noNonNullAssertion: config handlers are always defined
  const errorHandler = errorConfig.errorConfig!.errorHandler!;
  const responseTuple = errorConfig.responseInterceptors?.[0] as [
    (response: {
      data?: unknown;
      config?: Record<string, unknown>;
    }) => Promise<{ data?: unknown }> | { data?: unknown },
    (error: unknown) => Promise<unknown>,
  ];
  const onFulfilled = responseTuple[0];
  const onRejected = responseTuple[1];

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'location', {
      writable: true,
      // 浏览器完整路径含 APP_BASE；redirect 应去掉 /admin
      value: { pathname: '/admin/welcome', search: '', hash: '' },
    });
  });

  describe('errorThrower', () => {
    it('should throw when FastAPI code !== 0', () => {
      expect(() => {
        errorThrower({
          code: 40000,
          message: '参数错误',
          data: null,
        });
      }).toThrow('参数错误');
    });

    it('should not throw when FastAPI code === 0', () => {
      expect(() => {
        errorThrower({
          code: 0,
          message: 'ok',
          data: { id: 1 },
        });
      }).not.toThrow();
    });

    it('should throw BizError with redirect for 40100', () => {
      expect.assertions(3);
      try {
        errorThrower({
          code: 40100,
          message: '未登录或登录已过期',
          data: null,
        });
      } catch (error: any) {
        expect(error.name).toBe('BizError');
        expect(error.info.errorCode).toBe(40100);
        expect(error.info.showType).toBe(9);
      }
    });

    it('should throw when Pro mock success is false', () => {
      expect(() => {
        errorThrower({
          success: false,
          data: null,
          errorCode: 400,
          errorMessage: 'Bad Request',
          showType: 2,
        });
      }).toThrow('Bad Request');
    });
  });

  describe('errorHandler', () => {
    it('should rethrow when skipErrorHandler is true', () => {
      const error = new Error('Test error');
      expect(() => {
        errorHandler(error, { skipErrorHandler: true });
      }).toThrow('Test error');
    });

    it('should show error message for BizError', () => {
      const error: any = new Error('业务失败');
      error.name = 'BizError';
      error.info = {
        errorCode: 40000,
        errorMessage: '业务失败',
        showType: 2,
      };

      errorHandler(error, {});
      expect(message.error).toHaveBeenCalledWith('业务失败');
    });

    it('should redirect on unauthorized without retrying here', () => {
      const error: any = new Error('未登录或登录已过期');
      error.name = 'BizError';
      error.info = {
        errorCode: 40100,
        errorMessage: '未登录或登录已过期',
        showType: 9,
      };

      errorHandler(error, {
        url: '/api/v1/admin/users/me',
        method: 'GET',
      });

      // 换发/重试已迁移到 response 拦截器
      expect(mockTryRefreshTokens).not.toHaveBeenCalled();
      expect(mockRequest).not.toHaveBeenCalled();
      expect(message.error).toHaveBeenCalledWith('未登录或登录已过期');
      expect(mockClearTokens).toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalledWith(
        expect.stringContaining('/user/login?redirect='),
      );
    });

    it('should redirect when unauthorized HTTP 401 reaches errorHandler', () => {
      const error: any = new Error('Axios error');
      error.response = {
        status: 401,
        data: {
          code: 40100,
          message: '未登录或登录已过期',
          data: null,
        },
      };

      errorHandler(error, {
        url: '/api/v1/admin/users/me',
        method: 'GET',
      });

      expect(mockTryRefreshTokens).not.toHaveBeenCalled();
      expect(message.error).toHaveBeenCalledWith('未登录或登录已过期');
      expect(mockClearTokens).toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalledWith(
        `/user/login?redirect=${encodeURIComponent('/welcome')}`,
      );
    });

    it('should redirect on auth whitelist 401 without refresh', () => {
      const error: any = new Error('用户名或密码错误');
      error.name = 'BizError';
      error.info = {
        errorCode: 40100,
        errorMessage: '用户名或密码错误',
        showType: 9,
      };

      errorHandler(error, {
        url: '/api/v1/admin/auth/login',
        method: 'POST',
      });

      expect(mockTryRefreshTokens).not.toHaveBeenCalled();
      expect(mockClearTokens).toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalled();
    });

    it('should handle FastAPI envelope in axios error response', () => {
      const error: any = new Error('Axios error');
      error.response = {
        status: 422,
        data: {
          code: 42200,
          message: '请求参数校验失败',
          data: { errors: [] },
        },
      };

      errorHandler(error, {});
      expect(message.error).toHaveBeenCalledWith('请求参数校验失败');
    });

    it('should handle offline error', () => {
      const error: any = new Error('Network error');
      error.request = {};

      const originalOnLine = navigator.onLine;
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false,
      });

      try {
        errorHandler(error, {});
        expect(message.error).toHaveBeenCalledWith(
          '网络不可用，请检查网络连接后重试。',
        );
      } finally {
        Object.defineProperty(navigator, 'onLine', {
          writable: true,
          value: originalOnLine,
        });
      }
    });
  });

  describe('requestInterceptors', () => {
    const interceptor = errorConfig.requestInterceptors?.[0] as (config: {
      url?: string;
      method?: string;
      headers?: Record<string, unknown>;
    }) => {
      url?: string;
      headers?: Record<string, unknown>;
    };

    it('should attach common headers and Authorization', () => {
      const result = interceptor({
        url: '/api/v1/admin/users',
        method: 'GET',
      });

      expect(result.headers?.['X-Channel']).toBe('2');
      expect(result.headers?.['X-Timestamp']).toBeTruthy();
      expect(result.headers?.['X-Sign']).toBeTruthy();
      expect(result.headers?.Authorization).toBe('Bearer test-token');
    });

    it('should skip Authorization on login whitelist', () => {
      const result = interceptor({
        url: '/api/v1/admin/auth/login',
        method: 'POST',
      });

      expect(result.headers?.Authorization).toBeUndefined();
      expect(result.headers?.['X-Channel']).toBe('2');
    });
  });

  describe('responseInterceptors', () => {
    it('should pass through successful envelope', async () => {
      const response = {
        data: { code: 0, message: 'ok', data: { ok: true } },
        config: { url: '/api/v1/admin/users/me', method: 'GET' },
      };
      await expect(onFulfilled(response)).resolves.toEqual(response);
    });

    it('should throw on failed envelope', async () => {
      await expect(
        onFulfilled({
          data: { code: 40300, message: '权限不足', data: null },
          config: { url: '/api/v1/admin/users', method: 'GET' },
        }),
      ).rejects.toThrow('权限不足');
    });

    it('should refresh and retry on HTTP 401 in error interceptor', async () => {
      mockTryRefreshTokens.mockResolvedValue(true);
      const retryResponse = {
        data: { code: 0, message: 'ok', data: { id: 1 } },
        status: 200,
      };
      mockRequest.mockResolvedValue(retryResponse);

      const error: any = new Error('Axios error');
      error.config = {
        url: '/api/v1/admin/users/me',
        method: 'get',
        headers: { Authorization: 'Bearer expired' },
      };
      error.response = {
        status: 401,
        data: {
          code: 40100,
          message: '未登录或登录已过期',
          data: null,
        },
      };

      const result = await onRejected(error);

      expect(mockTryRefreshTokens).toHaveBeenCalled();
      expect(mockRequest).toHaveBeenCalledWith(
        '/api/v1/admin/users/me',
        expect.objectContaining({
          method: 'get',
          getResponse: true,
          __isRetryAfterRefresh: true,
        }),
      );
      expect(result).toEqual(retryResponse);
      expect(mockClearTokens).not.toHaveBeenCalled();
    });

    it('should refresh and retry on 40100 envelope in success interceptor', async () => {
      mockTryRefreshTokens.mockResolvedValue(true);
      const retryResponse = {
        data: { code: 0, message: 'ok', data: { id: 1 } },
        status: 200,
      };
      mockRequest.mockResolvedValue(retryResponse);

      const result = await onFulfilled({
        data: {
          code: 40100,
          message: '未登录或登录已过期',
          data: null,
        },
        config: {
          url: '/api/v1/admin/missions/list',
          method: 'POST',
          data: { page: 1 },
        },
      });

      expect(mockTryRefreshTokens).toHaveBeenCalled();
      expect(mockRequest).toHaveBeenCalledWith(
        '/api/v1/admin/missions/list',
        expect.objectContaining({
          method: 'POST',
          getResponse: true,
          __isRetryAfterRefresh: true,
        }),
      );
      expect(result).toEqual(retryResponse);
    });

    it('should reject when refresh fails on HTTP 401', async () => {
      mockTryRefreshTokens.mockResolvedValue(false);

      const error: any = new Error('Axios error');
      error.config = {
        url: '/api/v1/admin/users/me',
        method: 'GET',
      };
      error.response = {
        status: 401,
        data: {
          code: 40100,
          message: '未登录或登录已过期',
          data: null,
        },
      };

      await expect(onRejected(error)).rejects.toBe(error);
      expect(mockTryRefreshTokens).toHaveBeenCalled();
      expect(mockRequest).not.toHaveBeenCalled();
    });

    it('should not refresh again after retry flag', async () => {
      const error: any = new Error('Axios error');
      error.config = {
        url: '/api/v1/admin/users/me',
        method: 'GET',
        __isRetryAfterRefresh: true,
      };
      error.response = {
        status: 401,
        data: { code: 40100, message: '未登录或登录已过期', data: null },
      };

      await expect(onRejected(error)).rejects.toBe(error);
      expect(mockTryRefreshTokens).not.toHaveBeenCalled();
    });
  });
});
