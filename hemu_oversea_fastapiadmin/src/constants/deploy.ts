/**
 * 管理端部署子路径（与 Nginx location /admin 对齐）。
 * 改此处即可同步 Umi base / publicPath 与浏览器跳转逻辑；勿用环境变量覆盖。
 */
export const APP_BASE = '/admin';

/** 静态资源 publicPath，须以 / 结尾 */
export const APP_PUBLIC_PATH = `${APP_BASE}/`;

/** 登录页（Umi history 内路径，不含 APP_BASE） */
export const APP_LOGIN_PATH = '/user/login';

function normalizePath(path: string): string {
  if (!path) {
    return '/';
  }
  return path.startsWith('/') ? path : `/${path}`;
}

/**
 * 将 Umi 路由路径拼成浏览器完整 pathname（含 APP_BASE）。
 * 已带 base 的路径不会重复拼接。
 */
export function withAppBase(path: string): string {
  const normalized = normalizePath(path);
  if (!APP_BASE || APP_BASE === '/') {
    return normalized;
  }
  if (normalized === APP_BASE || normalized.startsWith(`${APP_BASE}/`)) {
    return normalized === APP_BASE ? `${APP_BASE}/` : normalized;
  }
  if (normalized === '/') {
    return `${APP_BASE}/`;
  }
  return `${APP_BASE}${normalized}`;
}

/**
 * 从浏览器 pathname 去掉 APP_BASE，得到 Umi 路由 pathname。
 */
export function stripAppBase(pathname: string): string {
  const normalized = normalizePath(pathname);
  if (!APP_BASE || APP_BASE === '/') {
    return normalized;
  }
  if (normalized === APP_BASE || normalized === `${APP_BASE}/`) {
    return '/';
  }
  if (normalized.startsWith(`${APP_BASE}/`)) {
    return normalized.slice(APP_BASE.length) || '/';
  }
  return normalized;
}

/** 判断浏览器 pathname 是否对应某个 Umi 路由路径 */
export function isAppRoutePath(pathname: string, routePath: string): boolean {
  return stripAppBase(pathname) === normalizePath(routePath);
}
