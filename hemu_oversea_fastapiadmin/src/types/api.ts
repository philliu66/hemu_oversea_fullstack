/** FastAPI 统一响应信封：{ code, message, data } */
export type ApiResponse<T = unknown> = {
  code: number;
  message: string;
  data: T | null;
};

/** 分页 data */
export type PageData<T = unknown> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

/** 登录返回的双 token */
export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
};

/** 管理端用户公开信息（与后端 UserPublic 对齐） */
export type UserPublic = {
  id: number;
  username: string;
  nickname: string;
  email: string;
  phone: string | null;
  avatar_url: string | null;
  role: string;
  org_type: string;
  supplier_id: number | null;
  created_by: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

/** 登录成功：token + 当前用户 */
export type AuthLoginResponse = TokenPair & {
  user: UserPublic;
};

/** 管理端供应商公开信息（与后端 SupplierPublic 对齐） */
export type SupplierPublic = {
  id: number;
  code: string;
  name: string;
  phone: string;
  email: string;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

/** 供应商详情（含管理员账号） */
export type SupplierDetailPublic = SupplierPublic & {
  admin_username: string | null;
};

/** POST /api/v1/admin/suppliers/list */
export type SupplierListParams = {
  keyword?: string;
  page?: number;
  page_size?: number;
};

/** POST /api/v1/admin/suppliers/create */
export type SupplierCreateParams = {
  name: string;
  phone: string;
  email: string;
  admin_username: string;
  /** 明文密码 */
  admin_password: string;
};

/** POST /api/v1/admin/suppliers/update */
export type SupplierUpdateParams = {
  id: number;
  name?: string;
  phone?: string;
  email?: string;
};

/** POST /api/v1/admin/supplier-staff/list */
export type SupplierStaffListParams = {
  keyword?: string;
  page?: number;
  page_size?: number;
};

/** POST /api/v1/admin/supplier-staff/create */
export type SupplierStaffCreateParams = {
  username: string;
  password: string;
  nickname?: string;
  email: string;
  phone?: string;
};

/** POST /api/v1/admin/supplier-staff/update */
export type SupplierStaffUpdateParams = {
  id: number;
  nickname?: string;
  email?: string;
  phone?: string;
  /** 可选：重置明文密码 */
  password?: string;
};

/** POST /api/v1/admin/supplier-staff/status */
export type SupplierStaffStatusParams = {
  id: number;
  is_active: boolean;
};

/** 店铺类型（与后端 StoreType 对齐） */
export type StoreType = 'dhgate' | 'tiktok';

/** 授权状态：0 未授权，1 已授权，2 授权已过期 */
export type StoreOauthStatus = 0 | 1 | 2;

/** 管理端店铺列表/创建/更新返回（与后端 StorePublic 对齐） */
export type StorePublic = {
  id: number;
  supplier_id?: number | null;
  store_type: StoreType | string;
  name: string;
  identifier: string;
  oauth_status: StoreOauthStatus | number;
  /** refresh_token 到期时间 */
  refresh_token_expires_at: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
};

/** 管理端店铺详情（与后端 StoreDetailPublic 对齐） */
export type StoreDetailPublic = StorePublic & {
  account: string;
  password: string;
};

/** POST /api/v1/admin/stores/authorize-url 返回 */
export type StoreAuthorizePublic = {
  store_id: number;
  store_type: string;
  authorize_url: string;
};

/** POST /api/v1/admin/stores/list */
export type StoreListParams = {
  keyword?: string;
  store_type?: StoreType;
  supplier_id?: number;
  page?: number;
  page_size?: number;
};

/** POST /api/v1/admin/stores/inspection/punish */
export type StoreInspectionPunishParams = {
  supplier_id: number;
  /** 不传则查该供应商下全部已授权敦煌店铺 */
  store_id?: number;
  query_days: number;
  page_no?: number;
  page_size?: number;
};

/** 店铺巡检处罚汇总返回（与后端 StoreInspectionPunishPublic 对齐） */
export type StoreInspectionPunishPublic = {
  /** 处罚列表（序列化别名 list） */
  list?: Record<string, unknown>[];
  /** 兼容按字段名序列化 */
  items?: Record<string, unknown>[];
  start_date: string;
  end_date: string;
};

/** POST /api/v1/admin/stores/create */
export type StoreCreateParams = {
  store_type: StoreType;
  name: string;
  identifier: string;
  account: string;
  password: string;
};

/** POST /api/v1/admin/stores/update */
export type StoreUpdateParams = {
  id: number;
  store_type?: StoreType;
  name?: string;
  identifier?: string;
  account?: string;
  password?: string;
};

/** POST /api/v1/admin/categories/dh/list */
export type DhCategoryListParams = {
  /** 父类目 cate_pub_id；不传则查一级类目 */
  parent_id?: string | null;
};

/** 敦煌商品分类（与后端 DhCategoryPublic 对齐） */
export type DhCategoryPublic = {
  id: number;
  cate_pub_id: string;
  pub_name: string;
  pub_name_cn: string | null;
  remark: string | null;
  leaf: string;
  pare_cate_pub_id: string | null;
  is_leaf: boolean;
};

/** 种子商品分类（与后端 DhSeedCategoryPublic 对齐） */
export type DhSeedCategoryPublic = DhCategoryPublic & {
  /** 该类目下种子商品数量（含子类目汇总） */
  product_count: number;
};

/** POST /api/v1/admin/categories/dh/path */
export type DhCategoryPathPublic = {
  id: number;
  cate_pub_id: string;
  path_name: string;
  path_items: DhCategoryPublic[];
};

/** 类目属性可选值 */
export type DhCategoryAttrValPublic = {
  cate_pub_attrval_id: number | null;
  cate_pub_attr_id: number | null;
  attr_val_id: string;
  pic_url: string | null;
  line_attrval_name: string | null;
  line_attrval_name_cn: string | null;
};

/** 类目属性定义 */
export type DhCategoryAttrPublic = {
  cate_pub_attr_id: number | null;
  attr_id: string;
  cate_pub_id: string | null;
  required: string;
  located: string;
  sale_attr: string;
  buy_attr: string;
  style: string;
  type: string;
  defined: string;
  is_brand: string;
  line_attr_name: string | null;
  line_attr_name_cn: string | null;
  isother: string;
  child_attr_id: string | null;
  values: DhCategoryAttrValPublic[];
};

/** POST /api/v1/admin/categories/dh/attrs */
export type DhCategoryAttrsPublic = {
  id: number;
  cate_pub_id: string;
  pub_name: string;
  pub_name_cn: string | null;
  leaf: string;
  attrs: DhCategoryAttrPublic[];
};

/** 商品产品属性值（对应 dh.item.get itemAttrValList） */
export type DhProductSelectedAttrValPublic = {
  attr_val_id?: string | null;
  /** 值级属性英文名（自定义属性的属性名，如 Function/Voltage） */
  attr_name?: string | null;
  /** 值级属性中文名 */
  attr_name_cn?: string | null;
  line_attrval_name?: string | null;
  line_attrval_name_cn?: string | null;
  pic_url?: string | null;
  brand_id?: string | null;
};

/** 商品自定义规格（对应 dh.item.get itemSpecSelfDefList） */
export type DhProductSpecSelfDefPublic = {
  attr_val_id: string | null;
  spec_attr_name: string | null;
  attr_val_name: string | null;
  pic_url: string | null;
};

/**
 * 商品产品属性（对应 dh.item.get itemAttrList，仅展示不参与 SKU）。
 * attr_id=11 自定义属性；attr_id=99 品牌属性；其余为类目属性。
 */
export type DhProductSelectedAttrPublic = {
  attr_id: string;
  attr_name: string | null;
  attr_name_cn: string | null;
  is_brand?: string | null;
  values: DhProductSelectedAttrValPublic[];
};

/** 商品列表类型：0=全部，1=仅种子商品 */
export type DhProductListType = 0 | 1;

/** 商品列表排序：0=同步时间倒序，1=同步时间正序 */
export type DhProductSort = 0 | 1;

/** POST /api/v1/admin/product/dh/list */
export type DhProductListParams = {
  type?: DhProductListType;
  /** 商品状态编码，如 100100 */
  state?: string;
  item_code?: string;
  item_name?: string;
  store_id?: number;
  /** 发布类目 ID；传入后筛选该类目及其下级 */
  cate_pub_id?: string;
  sort?: DhProductSort;
  page?: number;
  page_size?: number;
};

/** 敦煌商品列表项（与后端 DhProductPublic 对齐） */
export type DhProductPublic = {
  id: number;
  store_id: number;
  item_code: string;
  site_id: string;
  is_seed: string;
  supplier_id: string | null;
  cate_pub_id: string | null;
  state: string | null;
  item_name: string | null;
  short_desc: string | null;
  min_wholesale_qty: number | null;
  max_sale_qty: number | null;
  leading_time: number | null;
  price_min: string | number | null;
  price_max: string | number | null;
  sku_count: number | null;
  total_inventory: number | null;
  main_image_url: string | null;
  expire_date: string | null;
  operate_date: string | null;
  last_synced_at: string | null;
  sync_state?: string;
  sync_state_desc?: string | null;
  created_at: string;
  updated_at: string;
};

/** 敦煌商品 SKU（与后端 DhProductSkuPublic 对齐） */
export type DhProductSkuPublic = {
  id: number;
  sku_id: string | null;
  sku_code: string | null;
  retail_price: string | number | null;
  inventory: number | null;
  sale_status: string | null;
  pic_url: string | null;
  attr_combo_text: string | null;
};

/** 敦煌商品详情（与后端 DhProductDetailPublic 对齐） */
export type DhProductDetailPublic = {
  id: number;
  store_id: number;
  item_code: string;
  site_id: string;
  is_seed: string;
  supplier_id: string | null;
  cate_pub_id: string | null;
  state: string | null;
  item_name: string | null;
  short_desc: string | null;
  html_content: string | null;
  key_word1: string | null;
  key_word2: string | null;
  key_word3: string | null;
  video_url: string | null;
  min_wholesale_qty: number | null;
  max_sale_qty: number | null;
  leading_time: number | null;
  price_config_type: string | null;
  gross_weight: string | number | null;
  length: string | number | null;
  width: string | number | null;
  height: string | number | null;
  packing_quantity: number | null;
  price_min: string | number | null;
  price_max: string | number | null;
  sku_count: number | null;
  total_inventory: number | null;
  issample: string | null;
  is_dh_optimized: string | null;
  vaild_day: string | null;
  expire_date: string | null;
  operate_date: string | null;
  last_synced_at: string | null;
  sync_state: string;
  sync_state_desc: string | null;
  created_at: string;
  updated_at: string;
  img_list: string[];
  sku_list: DhProductSkuPublic[];
  category: DhCategoryPublic | null;
  attr_list?: DhProductSelectedAttrPublic[];
  /** 自定义规格（对应 dh.item.get itemSpecSelfDefList） */
  item_spec_self_def_list?: DhProductSpecSelfDefPublic[];
};
