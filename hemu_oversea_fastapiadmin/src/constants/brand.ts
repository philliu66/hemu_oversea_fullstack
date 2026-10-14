/** 系统标题后缀（统一改这里即可同步登录页 / 导航 / 页脚 / 欢迎页） */
export const SYSTEM_TITLE_SUFFIX = '跨境Fast系统';

/** 拼接展示标题：供应商账号带前缀，平台账号仅后缀 */
export function buildSystemTitle(supplierName?: string | null): string {
  const name = (supplierName || '').trim();
  return name ? `${name}${SYSTEM_TITLE_SUFFIX}` : SYSTEM_TITLE_SUFFIX;
}
