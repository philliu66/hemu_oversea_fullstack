/**
 * @see https://umijs.org/docs/max/access#access
 * */
export default function access(
  initialState: { currentUser?: API.CurrentUser } | undefined,
) {
  const { currentUser } = initialState ?? {};
  const role = currentUser?.access || currentUser?.role;
  const isSuperAdmin = role === 'super_admin';
  const isPlatformStaff = role === 'platform_staff';
  const isSupplierAdmin = role === 'supplier_admin';
  const isSupplierStaff = role === 'supplier_staff';
  return {
    canAdmin: isSuperAdmin || role === 'admin',
    /** 平台侧：超级管理员 / 平台员工（供应商增改等） */
    canPlatform: isSuperAdmin || isPlatformStaff,
    /** 仅超级管理员（供应商删除等） */
    canSuperAdmin: isSuperAdmin,
    /** 供应商管理员（员工管理等） */
    canSupplierAdmin: isSupplierAdmin,
    /** 供应商身份：管理员或员工 */
    canSupplier: isSupplierAdmin || isSupplierStaff,
  };
}
