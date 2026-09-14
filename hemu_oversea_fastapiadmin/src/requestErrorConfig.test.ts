import { message, notification } from 'antd';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { errorConfig } from './requestErrorConfig';

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
    replace: vi.fn(),
  },
  getIntl: vi.fn(() => ({
    formatMessage: vi.fn(({ defaultMessage }) => defaultMessage),
  })),
}));

vi.mock('@/utils/authToken', () => ({
  clearTokens: vi.fn(),
  getAccessToken: vi.fn(() => 'test-token'),
}));

describe('requestErrorConfig', () => {
  // biome-ignore lint/style/noNonNullAssertion: config handlers are always defined
  const errorThrower = errorConfig.errorConfig!.errorThrower!;
  // biome-ignore lint/style/noNonNullAssertion: config handlers are always defined
  const errorHandler = errorConfig.errorConfig!.errorHandler!;

  beforeEach(() => {
    vi.clearAllMocks();
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
    const interceptor = errorConfig.responseInterceptors?.[0] as (response: {
      data?: unknown;
    }) => { data?: unknown };

    it('should pass through successful envelope', () => {
      const response = {
        data: { code: 0, message: 'ok', data: { ok: true } },
      };
      expect(interceptor(response)).toEqual(response);
    });

    it('should throw on failed envelope', () => {
      expect(() => {
        interceptor({
          data: { code: 40300, message: '权限不足', data: null },
        });
      }).toThrow('权限不足');
    });
  });
});
