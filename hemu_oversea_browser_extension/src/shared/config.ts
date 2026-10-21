/** 扩展与页面约定的 source，防伪造 */
export const EXT_SOURCE = 'hemu-browser-ext' as const;
export const ADMIN_PAGE_SOURCE = 'hemu-admin-page' as const;

/** 协议版本，不兼容时管理端应提示升级扩展 */
export const PROTOCOL_VERSION = 1;

/** 扩展自身版本（与 package.json / manifest 对齐，发版时改） */
export const EXTENSION_VERSION = '0.1.0';
