import { describe, expect, it } from 'vitest';
import access from './access';

describe('access', () => {
  it('should return canAdmin true when user has admin access', () => {
    const initialState = {
      currentUser: {
        userid: '1',
        name: 'Admin User',
        avatar: 'https://example.com/avatar.png',
        access: 'admin',
      },
    };

    const result = access(initialState);

    expect(result.canAdmin).toBe(true);
  });

  it('should return canAdmin false when user has non-admin access', () => {
    const initialState = {
      currentUser: {
        userid: '2',
        name: 'Regular User',
        avatar: 'https://example.com/avatar.png',
        access: 'user',
      },
    };

    const result = access(initialState);

    expect(result.canAdmin).toBe(false);
  });

  it('should return canAdmin false when user access is undefined', () => {
    const initialState = {
      currentUser: {
        userid: '3',
        name: 'Guest User',
        avatar: 'https://example.com/avatar.png',
      },
    };

    const result = access(initialState);

    expect(result.canAdmin).toBe(false);
  });

  it('should return canAdmin false when currentUser is undefined', () => {
    const initialState = {
      currentUser: undefined,
    };

    const result = access(initialState);

    expect(result.canAdmin).toBeFalsy();
  });

  it('should return canSupplier for supplier admin and staff', () => {
    expect(
      access({
        currentUser: {
          userid: '4',
          name: 'Supplier Admin',
          access: 'supplier_admin',
        },
      }).canSupplier,
    ).toBe(true);
    expect(
      access({
        currentUser: {
          userid: '5',
          name: 'Supplier Staff',
          access: 'supplier_staff',
        },
      }).canSupplier,
    ).toBe(true);
    expect(
      access({
        currentUser: {
          userid: '6',
          name: 'Platform',
          access: 'platform_staff',
        },
      }).canSupplier,
    ).toBe(false);
  });
});
