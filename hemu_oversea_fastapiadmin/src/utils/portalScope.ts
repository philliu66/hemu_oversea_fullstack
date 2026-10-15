/** 门户身份与供应商作用域工具 */

export function isPlatformRole(role?: string | null): boolean {
  return role === 'platform_admin' || role === 'platform_staff';
}

export function isSupplierPortalRole(role?: string | null): boolean {
  return role === 'supplier_admin' || role === 'supplier_staff';
}

/**
 * 解析请求应携带的 supplier_id。
 * - 供应商角色：用账号绑定值
 * - 平台角色：用页面选中值（未选则 undefined，调用方应跳过请求）
 */
export function resolveRequestSupplierId(
  currentUser:
    | { role?: string; access?: string; supplier_id?: number | null }
    | undefined
    | null,
  selectedSupplierId?: number | null,
): number | undefined {
  const role = currentUser?.access || currentUser?.role;
  if (isSupplierPortalRole(role)) {
    return currentUser?.supplier_id ?? undefined;
  }
  if (isPlatformRole(role)) {
    return selectedSupplierId ?? undefined;
  }
  return selectedSupplierId ?? currentUser?.supplier_id ?? undefined;
}

/** 平台角色且尚未选择供应商时返回 true */
export function needsSupplierSelection(
  currentUser:
    | { role?: string; access?: string; supplier_id?: number | null }
    | undefined
    | null,
  selectedSupplierId?: number | null,
): boolean {
  const role = currentUser?.access || currentUser?.role;
  return isPlatformRole(role) && (selectedSupplierId == null || selectedSupplierId <= 0);
}
