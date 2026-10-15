/** 业务成功码（FastAPI ApiResponse.code） */
export const API_SUCCESS_CODE = 0;

/** 管理端渠道号，对应请求头 X-Channel */
export const API_CHANNEL = 2;

/** access / refresh 本地存储 key */
export const ACCESS_TOKEN_KEY = 'hemu_admin_access_token';
export const REFRESH_TOKEN_KEY = 'hemu_admin_refresh_token';

/** 管理端认证相关路径 */
export const AdminAuthApi = {
  CAPTCHA: '/api/v1/admin/auth/captcha',
  LOGIN: '/api/v1/admin/auth/login',
  REFRESH: '/api/v1/admin/auth/refresh',
  LOGOUT: '/api/v1/admin/auth/logout',
  LOGOUT_ALL: '/api/v1/admin/auth/logout-all',
  PASSWORD: '/api/v1/admin/auth/password',
} as const;

/** 管理端用户相关路径 */
export const AdminUserApi = {
  ME: '/api/v1/admin/users/me',
  LIST: '/api/v1/admin/users',
  SUPPLIER_LIST: '/api/v1/admin/users/supplier-list',
} as const;

/** 管理端供应商相关路径 */
export const AdminSupplierApi = {
  OPTIONS: '/api/v1/admin/suppliers/options',
  LIST: '/api/v1/admin/suppliers/list',
  DETAIL: '/api/v1/admin/suppliers/detail',
  CREATE: '/api/v1/admin/suppliers/create',
  UPDATE: '/api/v1/admin/suppliers/update',
  DELETE: '/api/v1/admin/suppliers/delete',
} as const;

/** 管理端供应商员工相关路径 */
export const AdminSupplierStaffApi = {
  LIST: '/api/v1/admin/supplier-staff/list',
  CREATE: '/api/v1/admin/supplier-staff/create',
  UPDATE: '/api/v1/admin/supplier-staff/update',
  STATUS: '/api/v1/admin/supplier-staff/status',
  DELETE: '/api/v1/admin/supplier-staff/delete',
} as const;

/** 管理端店铺相关路径 */
export const AdminStoreApi = {
  LIST: '/api/v1/admin/stores/list',
  DETAIL: '/api/v1/admin/stores/detail',
  BASE_DISCOUNT: '/api/v1/admin/stores/base-discount/get',
  AUTHORIZE_URL: '/api/v1/admin/stores/authorize-url',
  CREATE: '/api/v1/admin/stores/create',
  UPDATE: '/api/v1/admin/stores/update',
  DELETE: '/api/v1/admin/stores/delete',
  INSPECTION_PUNISH: '/api/v1/admin/stores/inspection/punish',
  GROUPS: '/api/v1/admin/stores/groups',
  SHIPPING_TEMPLATE_LIST: '/api/v1/admin/stores/shipping-template/list',
  AFTERSALE_TEMPLATE_LIST: '/api/v1/admin/stores/aftersale-template/list',
} as const;

/** 管理端商品相关路径 */
export const AdminProductApi = {
  DH_PRODUCT_LIST: '/api/v1/admin/product/dh/list',
  DH_PRODUCT_DETAIL: '/api/v1/admin/product/dh/detail',
  DH_SKU_LIST_PRICE: '/api/v1/admin/product/dh/skulistprice/get',
  DH_PRODUCT_PUBLISH: '/api/v1/admin/product/dh/publish',
} as const;

/** 管理端任务相关路径 */
export const AdminMissionApi = {
  LIST: '/api/v1/admin/missions/list',
  DETAIL: '/api/v1/admin/missions/detail',
  CREATE: '/api/v1/admin/missions/create',
  UPDATE: '/api/v1/admin/missions/update',
  MARK_FINISHED: '/api/v1/admin/missions/mark-finished',
  FISSION_DATA_LIST: '/api/v1/admin/missions/fission-data/list',
  FISSION_DATA_DETAIL: '/api/v1/admin/missions/fission-data/detail',
  FISSION_DATA_ADD: '/api/v1/admin/missions/fission-data/add',
  FISSION_DATA_UPDATE: '/api/v1/admin/missions/fission-data/update',
  FISSION_DATA_DELETE: '/api/v1/admin/missions/fission-data/delete',
  FISSION_DATA_MARK_FINISHED:
    '/api/v1/admin/missions/fission-data/mark-finished',
  FISSION_DATA_IMPORT: '/api/v1/admin/missions/fission-data/import',
  LOGS_LIST: '/api/v1/admin/missions/logs/list',
  EXECUTE: '/api/v1/admin/missions/execute',
} as const;

/** 管理端商品分类相关路径 */
export const AdminCategoryApi = {
  DH_LIST: '/api/v1/admin/categories/dh/list',
  DH_SEED_LIST: '/api/v1/admin/categories/dh/seed-list',
  DH_SEARCH: '/api/v1/admin/categories/dh/search',
  DH_PATH: '/api/v1/admin/categories/dh/path',
  DH_ATTRS: '/api/v1/admin/categories/dh/attrs',
  DH_COMMISSION_RATE: '/api/v1/admin/categories/dh/commission-rate/get',
} as const;

/** 管理端模版相关路径 */
export const AdminTemplateApi = {
  SKU_ATTR_LIST: '/api/v1/admin/templates/dh/sku-attr-templates/list',
  SKU_ATTR_DETAIL: '/api/v1/admin/templates/dh/sku-attr-templates/detail',
  SKU_ATTR_CREATE: '/api/v1/admin/templates/dh/sku-attr-templates/create',
  SKU_ATTR_UPDATE: '/api/v1/admin/templates/dh/sku-attr-templates/update',
  SKU_ATTR_DELETE: '/api/v1/admin/templates/dh/sku-attr-templates/delete',
  SKU_ATTR_LOOKUP: '/api/v1/admin/templates/dh/sku-attr-templates/lookup',
} as const;

/** 管理端 SKU 相关路径 */
export const AdminSkuApi = {
  BASE_INFO_LIST: '/api/v1/admin/sku/dh/base-info/list',
} as const;

/** 全局工具类路径 */
export const CommonUtilsApi = {
  DHGATE_UPLOAD_IMG: '/api/v1/common/utils/dhgate/uploadimg',
  DHGATE_TWEAK_IMG: '/api/v1/common/utils/dhgate/tweakimg',
  DHGATE_GET_MEASURES_UNIT_LIST:
    '/api/v1/common/utils/dhgate/getmeasuresunitlist',
  DHGATE_GET_SKU_BASE_INFO: '/api/v1/common/utils/dhgate/getskubaseinfo',
} as const;

/** 列表默认分页大小 */
export const PAGE_SIZE_DEFAULT = 10;

/**
 * 无需 access_token 的白名单（方法 + 路径后缀匹配）。
 * logout 仅依赖 refresh_token body，不强制带 Bearer。
 */
export const AUTH_WHITELIST = [
  { method: 'GET', path: AdminAuthApi.CAPTCHA },
  { method: 'POST', path: AdminAuthApi.LOGIN },
  { method: 'POST', path: AdminAuthApi.REFRESH },
  { method: 'POST', path: AdminAuthApi.LOGOUT },
] as const;
