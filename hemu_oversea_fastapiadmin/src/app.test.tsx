import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  mockReplace,
  mockHistory,
  mockGetAdminCurrentUser,
  mockGetAdminSystemConfig,
  mockTryRefreshTokens,
  mockClearTokens,
  mockGetAccessToken,
  mockGetRefreshToken,
} = vi.hoisted(() => {
  const replace = vi.fn();
  return {
    mockReplace: replace,
    mockHistory: {
      location: {
        pathname: '/welcome',
        search: '',
        hash: '',
      },
      replace,
    },
    mockGetAdminCurrentUser: vi.fn(),
    mockGetAdminSystemConfig: vi.fn(),
    mockTryRefreshTokens: vi.fn(),
    mockClearTokens: vi.fn(),
    mockGetAccessToken: vi.fn(),
    mockGetRefreshToken: vi.fn(),
  };
});

vi.mock('@umijs/max', () => ({
  history: mockHistory,
  Link: ({ children }: { children?: unknown }) => children,
}));

vi.mock('@/services/admin/auth', () => ({
  getAdminCurrentUser: (...args: unknown[]) => mockGetAdminCurrentUser(...args),
  getAdminSystemConfig: (...args: unknown[]) =>
    mockGetAdminSystemConfig(...args),
}));

vi.mock('./utils/authRefresh', () => ({
  tryRefreshTokens: (...args: unknown[]) => mockTryRefreshTokens(...args),
}));

vi.mock('./utils/authToken', () => ({
  clearTokens: (...args: unknown[]) => mockClearTokens(...args),
  getAccessToken: (...args: unknown[]) => mockGetAccessToken(...args),
  getRefreshToken: (...args: unknown[]) => mockGetRefreshToken(...args),
}));

vi.mock('@/utils/datetime', () => ({
  setupDayjs: vi.fn(),
}));

vi.mock('@/components/RightContent/AvatarName', () => ({
  default: () => null,
}));

vi.mock('@/components', () => ({
  AvatarDropdown: () => null,
  DocLink: () => null,
  ErrorBoundary: ({ children }: { children?: unknown }) => children,
  Footer: () => null,
  LangDropdown: () => null,
  OfflineBanner: () => null,
  VersionDropdown: () => null,
}));

vi.mock('@ant-design/pro-components', () => ({
  SettingDrawer: () => null,
}));

vi.mock('@ant-design/icons', () => ({
  LinkOutlined: () => null,
}));

vi.mock('./requestErrorConfig', () => ({
  errorConfig: {},
}));

vi.mock('../config/defaultSettings', () => ({
  default: { navTheme: 'light' },
}));

describe('app getInitialState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    mockHistory.location = {
      pathname: '/welcome',
      search: '',
      hash: '',
    };
    mockGetAccessToken.mockReturnValue('access-token');
    mockGetRefreshToken.mockReturnValue('refresh-token');
    mockTryRefreshTokens.mockResolvedValue(false);
    mockGetAdminSystemConfig.mockResolvedValue({ name: '合木跨境FAST系统' });
  });

  it('should fetch currentUser when not on login page', async () => {
    mockGetAdminCurrentUser.mockResolvedValue({
      name: 'Test User',
      access: 'admin',
    });

    const { getInitialState } = await import('./app');
    const state = await getInitialState();

    expect(mockGetAdminCurrentUser).toHaveBeenCalled();
    expect(mockGetAdminSystemConfig).toHaveBeenCalled();
    expect(state.currentUser).toEqual({
      name: 'Test User',
      access: 'admin',
    });
    expect(state.config).toEqual({ name: '合木跨境FAST系统' });
    expect(state.settingDrawerOpen).toBe(false);
    expect(state.fetchUserInfo).toBeDefined();
  });

  it('should refresh then fetch when access token expired', async () => {
    mockGetAdminCurrentUser
      .mockRejectedValueOnce(new Error('401 Unauthorized'))
      .mockResolvedValueOnce({
        name: 'Refreshed User',
        access: 'admin',
      });
    mockTryRefreshTokens.mockResolvedValue(true);

    const { getInitialState } = await import('./app');
    const state = await getInitialState();

    expect(mockTryRefreshTokens).toHaveBeenCalled();
    expect(mockGetAdminCurrentUser).toHaveBeenCalledTimes(2);
    expect(state.currentUser).toEqual({
      name: 'Refreshed User',
      access: 'admin',
    });
    expect(mockReplace).not.toHaveBeenCalled();
    expect(mockClearTokens).not.toHaveBeenCalled();
  });

  it('should redirect to login when refresh also fails', async () => {
    mockGetAdminCurrentUser.mockRejectedValue(new Error('401 Unauthorized'));
    mockTryRefreshTokens.mockResolvedValue(false);

    const { getInitialState } = await import('./app');
    const state = await getInitialState();

    expect(mockTryRefreshTokens).toHaveBeenCalled();
    expect(mockClearTokens).toHaveBeenCalled();
    expect(mockReplace).toHaveBeenCalledWith(
      expect.stringContaining('/user/login?redirect='),
    );
    expect(state.currentUser).toBeUndefined();
  });

  it('should not fetch currentUser on login page', async () => {
    mockHistory.location = {
      pathname: '/user/login',
      search: '',
      hash: '',
    };

    const { getInitialState } = await import('./app');
    const state = await getInitialState();

    expect(mockGetAdminCurrentUser).not.toHaveBeenCalled();
    expect(mockGetAdminSystemConfig).toHaveBeenCalled();
    expect(state.currentUser).toBeUndefined();
    expect(state.config).toEqual({ name: '合木跨境FAST系统' });
    expect(state.fetchUserInfo).toBeDefined();
  });

  it('should encode redirect path correctly on auth failure', async () => {
    mockHistory.location = {
      pathname: '/admin/users',
      search: '?page=2',
      hash: '#section',
    };
    mockGetAdminCurrentUser.mockRejectedValue(new Error('401'));
    mockTryRefreshTokens.mockResolvedValue(false);

    const { getInitialState } = await import('./app');
    await getInitialState();

    expect(mockReplace).toHaveBeenCalledWith(
      `/user/login?redirect=${encodeURIComponent('/admin/users?page=2#section')}`,
    );
  });

  it('should include default settings in initial state', async () => {
    mockGetAdminCurrentUser.mockResolvedValue({ name: 'User' });

    const { getInitialState } = await import('./app');
    const state = await getInitialState();

    expect(state.settings).toEqual({ navTheme: 'light' });
  });

  it('fetchUserInfo should return user data on success', async () => {
    mockGetAdminCurrentUser.mockResolvedValue({
      name: 'Fetched User',
      access: 'user',
    });

    const { getInitialState } = await import('./app');
    const state = await getInitialState();

    const user = await state.fetchUserInfo?.();
    expect(user).toEqual({ name: 'Fetched User', access: 'user' });
  });
});
