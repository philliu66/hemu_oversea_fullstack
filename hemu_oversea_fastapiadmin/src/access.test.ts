import { describe, expect, it } from 'vitest';
import access from './access';

describe('access', () => {
  it('should grant all to platform_admin', () => {
    const result = access({
      currentUser: {
        userid: '1',
        name: 'Admin',
        access: 'platform_admin',
        permission_codes: [],
      },
    });
    expect(result.canPlatformAdmin).toBe(true);
    expect(result.can('supplier.create')).toBe(true);
    expect(result.canAccessRoute({ routeId: 'mission.fission' })).toBe(true);
  });

  it('should check permission_codes for platform_staff', () => {
    const result = access({
      currentUser: {
        userid: '2',
        name: 'Staff',
        access: 'platform_staff',
        permission_codes: ['supplier.list', 'supplier.create'],
      },
    });
    expect(result.can('supplier.create')).toBe(true);
    expect(result.can('supplier.delete')).toBe(false);
    expect(result.canAccessRoute({ routeId: 'supplier.list' })).toBe(true);
  });

  it('should return false when currentUser is undefined', () => {
    const result = access({ currentUser: undefined });
    expect(result.canAdmin).toBeFalsy();
    expect(result.can('welcome')).toBe(false);
  });

  it('should return canSupplier for supplier admin and staff', () => {
    expect(
      access({
        currentUser: {
          userid: '4',
          name: 'Supplier Admin',
          access: 'supplier_admin',
          permission_codes: ['mission.fission'],
        },
      }).canSupplier,
    ).toBe(true);
    expect(
      access({
        currentUser: {
          userid: '5',
          name: 'Supplier Staff',
          access: 'supplier_staff',
          permission_codes: [],
        },
      }).canSupplier,
    ).toBe(true);
  });
});
