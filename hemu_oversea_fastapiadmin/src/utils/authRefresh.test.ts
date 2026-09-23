import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockAdminRefresh, mockGetRefreshToken } = vi.hoisted(() => ({
  mockAdminRefresh: vi.fn(),
  mockGetRefreshToken: vi.fn(),
}));

vi.mock('@/services/admin/auth', () => ({
  adminRefresh: (...args: unknown[]) => mockAdminRefresh(...args),
}));

vi.mock('@/utils/authToken', () => ({
  getRefreshToken: (...args: unknown[]) => mockGetRefreshToken(...args),
}));

describe('authRefresh', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetModules();
    const { resetAuthRefreshState } = await import('./authRefresh');
    resetAuthRefreshState();
  });

  it('should return false when no refresh token', async () => {
    mockGetRefreshToken.mockReturnValue('');
    const { tryRefreshTokens } = await import('./authRefresh');

    await expect(tryRefreshTokens()).resolves.toBe(false);
    expect(mockAdminRefresh).not.toHaveBeenCalled();
  });

  it('should return true when refresh succeeds', async () => {
    mockGetRefreshToken.mockReturnValue('refresh-token');
    mockAdminRefresh.mockResolvedValue({
      access_token: 'a',
      refresh_token: 'b',
    });
    const { tryRefreshTokens } = await import('./authRefresh');

    await expect(tryRefreshTokens()).resolves.toBe(true);
    expect(mockAdminRefresh).toHaveBeenCalledTimes(1);
  });

  it('should single-flight concurrent refresh calls', async () => {
    mockGetRefreshToken.mockReturnValue('refresh-token');
    let resolveRefresh: (() => void) | undefined;
    mockAdminRefresh.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRefresh = () =>
            resolve({ access_token: 'a', refresh_token: 'b' });
        }),
    );

    const { tryRefreshTokens } = await import('./authRefresh');

    const p1 = tryRefreshTokens();
    const p2 = tryRefreshTokens();
    expect(mockAdminRefresh).toHaveBeenCalledTimes(1);

    resolveRefresh?.();
    await expect(Promise.all([p1, p2])).resolves.toEqual([true, true]);
  });

  it('should return false when refresh throws', async () => {
    mockGetRefreshToken.mockReturnValue('refresh-token');
    mockAdminRefresh.mockRejectedValue(new Error('refresh failed'));
    const { tryRefreshTokens } = await import('./authRefresh');

    await expect(tryRefreshTokens()).resolves.toBe(false);
  });
});
