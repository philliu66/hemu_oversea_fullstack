const ACCOUNT_ROLE_LABEL_ZH: Record<string, string> = {
  platform_admin: '平台管理员',
  platform_staff: '平台员工',
  supplier_admin: '供应商管理员',
  supplier_staff: '供应商员工',
  app_user: 'App 用户',
};

/** 账号角色展示名（未知角色原样返回） */
export function accountRoleLabel(role: string): string {
  return ACCOUNT_ROLE_LABEL_ZH[role] ?? role;
}
