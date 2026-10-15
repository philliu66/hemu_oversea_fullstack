/**
 * @see https://umijs.org/docs/max/access#access
 */
export default function access(
  initialState: { currentUser?: API.CurrentUser } | undefined,
) {
  const { currentUser } = initialState ?? {};
  const role = currentUser?.access || currentUser?.role;
  const codes = new Set(currentUser?.permission_codes ?? []);
  const isPlatformAdmin = role === 'platform_admin';
  const isPlatformStaff = role === 'platform_staff';
  const isSupplierAdmin = role === 'supplier_admin';
  const isSupplierStaff = role === 'supplier_staff';

  const has = (code?: string) => {
    if (!code) return true;
    if (isPlatformAdmin) return true;
    return codes.has(code);
  };

  const canPlatform = isPlatformAdmin || isPlatformStaff;
  const canSupplier = isSupplierAdmin || isSupplierStaff;

  return {
    canAdmin: isPlatformAdmin || role === 'admin',
    canPlatform,
    canPlatformAdmin: isPlatformAdmin,
    canSupplierAdmin: isSupplierAdmin,
    canSupplier,
    /**
     * 供应商侧业务数据（店铺/商品/模板/任务等）是否可写。
     * 平台角色默认只读；供应商门户按权限码控制。
     */
    canWriteSupplierData: canSupplier,
    /** 路由级：配合 routes.ts 的 access + routeId */
    canAccessRoute: (route: { routeId?: string }) => has(route.routeId),
    /** 按钮/任意权限码 */
    can: (code: string) => has(code),
    hasPermission: has,
  };
}
