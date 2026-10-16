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
  supplier_name?: string | null;
  created_by: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  permission_codes?: string[];
  roles?: { id: number; name: string }[];
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
  created_by_name?: string | null;
  created_at: string;
  updated_at: string;
};

/** 供应商下拉选项 */
export type SupplierOption = {
  id: number;
  name: string;
  code: string;
};

/** 供应商详情（含管理员账号） */
export type SupplierDetailPublic = SupplierPublic & {
  admin_username: string | null;
  permission_codes?: string[];
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
  permission_codes: string[];
};

/** 供应商每日巡检设置（与后端 SupplierInspectionSchedulePublic 对齐） */
export type SupplierInspectionSchedulePublic = {
  id: number;
  supplier_id: number;
  query_days: number;
  emails: string;
  created_at: string;
  updated_at: string;
  last_sent_at?: string | null;
  last_send_status?: string | null;
};

/** POST /api/v1/admin/suppliers/inspection-schedule/save */
export type SupplierInspectionScheduleSaveParams = {
  supplier_id?: number;
  query_days: 3 | 7 | 10;
  emails: string;
};

/** POST /api/v1/admin/suppliers/update */
export type SupplierUpdateParams = {
  id: number;
  name?: string;
  phone?: string;
  email?: string;
  permission_codes?: string[];
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
  role_ids?: number[];
};

/** POST /api/v1/admin/supplier-staff/update */
export type SupplierStaffUpdateParams = {
  id: number;
  nickname?: string;
  email?: string;
  phone?: string;
  /** 可选：重置明文密码 */
  password?: string;
  role_ids?: number[];
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
  supplier_name?: string | null;
  store_type: StoreType | string;
  name: string;
  identifier: string;
  /** 基础折扣（0.00～0.99） */
  base_discount: number | string;
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

/** POST /api/v1/admin/stores/base-discount/get */
export type StoreBaseDiscountPublic = {
  id: number;
  name: string;
  /** 基础折扣率（0.00～0.99） */
  base_discount: number | string;
};

/** 店铺售后模板 */
export type StoreAftersaleTemplatePublic = {
  after_sale_template_id: string;
  name?: string | null;
  if_template_default?: string | null;
};

/** 店铺物流（运费）模板，shipping_model_id 对应商品 shippingModelId */
export type StoreShippingTemplatePublic = {
  shipping_model_id: string;
  name?: string | null;
  model_type?: string | null;
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

/** POST /api/v1/admin/stores/inspection/dispute */
export type StoreInspectionDisputeParams = {
  supplier_id: number;
  /** 不传则查该供应商下全部已授权敦煌店铺 */
  store_id?: number;
  page_no?: number;
  page_size?: number;
};

/** 店铺巡检纠纷开启订单汇总（与后端 StoreInspectionDisputePublic 对齐） */
export type StoreInspectionDisputePublic = {
  /** 纠纷列表（序列化别名 list） */
  list?: Record<string, unknown>[];
  /** 兼容按字段名序列化 */
  items?: Record<string, unknown>[];
};

/** POST /api/v1/admin/stores/create */
export type StoreCreateParams = {
  store_type: StoreType;
  name: string;
  identifier: string;
  base_discount: number;
  account: string;
  password: string;
  supplier_id?: number;
};

/** POST /api/v1/admin/stores/update */
export type StoreUpdateParams = {
  id: number;
  store_type?: StoreType;
  name?: string;
  identifier?: string;
  base_discount?: number;
  account?: string;
  password?: string;
};

/** POST /api/v1/admin/categories/dh/list */
export type DhCategoryListParams = {
  /** 父类目 cate_pub_id；不传则查一级类目 */
  parent_id?: string | null;
  /** 种子分类查询时平台身份必填 */
  supplier_id?: number;
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

/** 阶梯佣金区间（对应 unitList 项） */
export type DhCommissionUnitPublic = {
  left_bound?: string | null;
  right_bound?: string | null;
  left_bound_close?: boolean | null;
  right_bound_close?: boolean | null;
  commission_rate?: string | null;
};

/** POST /api/v1/admin/categories/dh/commission-rate/get
 * 官方按二级类目绑定佣金率，cate_id 须为二级类目 ID
 */
export type DhCommissionRatePublic = {
  cate_id: string;
  unit_list: DhCommissionUnitPublic[];
};

/** 商品产品属性值（对应 dh.item.get itemAttrValList） */
export type DhProductSelectedAttrValPublic = {
  attr_id?: string | null;
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
  is_price_attr?: string | null;
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
  /** 平台身份必填 */
  supplier_id?: number;
};

/** 敦煌商品列表项（与后端 DhProductPublic 对齐） */
export type DhProductPublic = {
  id: number;
  store_id: number;
  store_name?: string | null;
  supplier_id?: number | null;
  supplier_name?: string | null;
  item_code: string;
  site_id: string;
  is_seed: string;
  cate_pub_id: string | null;
  state: string | null;
  item_name: string | null;
  main_image_url: string | null;
  last_synced_at: string | null;
  sync_state?: string;
};

/** 敦煌商品 SKU（与后端 DhProductSkuPublic 对齐） */
export type DhProductSkuPublic = {
  id: number;
  sku_id: string | null;
  sku_code: string | null;
  sku_md5?: string | null;
  retail_price: string | number | null;
  inventory: number | null;
  sale_status: string | null;
  pic_url: string | null;
  attr_combo_text: string | null;
  item_sku_attr_value_list?: DhItemSkuAttrValPublic[];
  item_sku_inventory_list?: DhItemSkuInventoryPublic[];
  shipto_country_price_list?: DhItemShiptoSkuPricePublic[];
};

export type DhItemSkuAttrValPublic = {
  attr_id?: string | null;
  attr_val_id?: string | null;
  attr_val_code?: string | null;
  size_spec_type?: string | null;
};

export type DhItemSkuInventoryPublic = {
  sku_md5?: string | null;
  inventory_location?: string | null;
  sku_inventory_qty?: number | null;
};

export type DhItemShiptoSkuPricePublic = {
  region_code?: string | null;
  retail_price?: string | number | null;
};

export type DhItemWholesaleRangePublic = {
  discount?: string | number | null;
  start_qty?: number | null;
};

/** 敦煌计件单位（measures_unit_dh / MeasureVO） */
export type DhMeasuresUnitPublic = {
  measure_id: string;
  name?: string | null;
  description?: string | null;
  valid?: string | null;
  cname?: string | null;
  short_name?: string | null;
  plural?: string | null;
};

/** 敦煌 SKU 基础信息（sku_base_info_dh） */
export type DhSkuBaseInfoPublic = {
  supplier_id: number;
  sku_code: string;
  sku_series: string;
  unit_price: string | number;
  shipping_template_name?: string | null;
  weight_kg?: string | number | null;
  packing_quantity?: number | null;
  min_wholesale_qty?: number | null;
};

/** POST /api/v1/admin/sku/dh/base-info/list */
export type DhSkuBaseInfoListParams = {
  keyword?: string;
  page?: number;
  page_size?: number;
  supplier_id?: number;
};

/** SKU 属性模版列表项 */
export type SkuAttrTemplateListItemPublic = {
  id: number;
  sku_code: string;
  cate_pub_id: string;
  cate_name?: string | null;
  category_id?: number | null;
  supplier_id?: number | null;
  supplier_name?: string | null;
  updated_at: string;
};

/** SKU 属性模版详情 */
export type SkuAttrTemplatePublic = {
  id: number;
  supplier_id: number;
  supplier_name?: string | null;
  sku_code: string;
  cate_pub_id: string;
  cate_name?: string | null;
  category_id?: number | null;
  raw_json: {
    attr_list?: DhProductSelectedAttrPublic[];
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
  created_by: number;
  updated_by: number;
};

export type SkuAttrTemplateListParams = {
  sku_code?: string;
  cate_pub_id?: string;
  page?: number;
  page_size?: number;
  supplier_id?: number;
};

export type SkuAttrTemplateCreateParams = {
  sku_code: string;
  cate_pub_id: string;
  supplier_id?: number;
  raw_json: {
    attr_list?: DhProductSelectedAttrPublic[];
    [key: string]: unknown;
  };
};

export type SkuAttrTemplateUpdateParams = SkuAttrTemplateCreateParams & {
  id: number;
};

/** POST /api/v1/admin/templates/dh/sku-attr-templates/lookup */
export type SkuAttrTemplateLookupParams = {
  cate_pub_id: string;
  sku_codes: string[];
  supplier_id?: number;
};

export type SkuAttrTemplateLookupItemPublic = {
  sku_code: string;
  found: boolean;
  raw_json?: {
    attr_list?: DhProductSelectedAttrPublic[];
    [key: string]: unknown;
  } | null;
};

export type SkuAttrTemplateLookupPublic = {
  items: SkuAttrTemplateLookupItemPublic[];
};

/** POST /api/v1/admin/product/dh/skulistprice/get */
export type DhSkuListPriceParams = {
  supplier_id: number;
  sku_code: string;
  store_id: number;
  cate_id?: string;
};

export type DhSkuListPricePublic = {
  supplier_id: number;
  sku_code: string;
  store_id: number;
  cate_id: string;
  unit_price: string | number;
  packing_quantity: number;
  min_wholesale_qty: number;
  sales_unit: number;
  order_amount: string | number;
  commission_rate: string | number;
  base_discount: string | number;
  list_price: string | number;
};

/** POST /api/v1/admin/product/dh/publish */
export type DhProductPublishType = 'addnew' | 'addfission';

export type DhProductPublishParams = {
  type?: DhProductPublishType;
  mission_data_fission_id?: number;
  info?: Record<string, unknown> | null;
  supplier_id?: number;
};

export type DhProductPublishPublic = {
  type: string;
  item_code?: string | null;
  mission_data_fission_id?: number | null;
  fission_status?: string | null;
  /** 最终上传给敦煌 dh.item.add 的参数（不含 htmlContent） */
  upload_dh_product_info?: Record<string, unknown> | null;
};

export type DhItemWeightRangePublic = {
  base_qt?: number | null;
  step_qt?: number | null;
  step_weight?: string | number | null;
};

export type DhItemInventoryLocationPublic = {
  sort_val?: number | null;
  leading_time?: number | null;
  inventory_location?: string | null;
  if_in_transit?: string | null;
};

export type DhItemInventoryPublic = {
  inventory_location?: string | null;
  inventory_status?: string | null;
  subtract_stock_type?: string | null;
  inventory_ori_qty?: number | null;
  inventory_qty?: number | null;
  inventory_location_list?: DhItemInventoryLocationPublic[];
};

export type DhItemShiptoSettingPublic = {
  region_code?: string | null;
  shipto_country_list?: string[];
  item_wholesale_range_list?: DhItemWholesaleRangePublic[];
};

export type DhItemCustomTypeInfoPublic = {
  custom_type?: string | null;
  retail_price?: string | number | null;
  min_wholesale_qty?: number | null;
  max_sale_qty?: number | null;
  leading_time?: number | null;
  sku_code?: string | null;
  sale_status?: string | null;
  shipto_country_price_list?: DhItemShiptoSkuPricePublic[];
};

export type DhItemAttrGroupDetailPublic = {
  attr_id?: string | null;
  attr_val_id?: string | null;
  attr_name?: string | null;
  attr_name_cn?: string | null;
  line_attrval_name?: string | null;
  line_attrval_name_cn?: string | null;
};

export type DhItemAttrGroupPublic = {
  item_attrgroup_detail_list?: DhItemAttrGroupDetailPublic[];
};

/** 敦煌商品图片（对应 dh.item.get itemImgList） */
export type DhProductImgPublic = {
  img_url: string | null;
  img_md5: string | null;
  type: string | null;
  /** 首次微调前的原图；有值且现图也有值则视为已微调 */
  original?: DhProductImgPublic | null;
};

/** POST /api/v1/common/utils/dhgate/uploadimg — 直接上传 */
export type DhgateImgInfoPublic = {
  img_url: string | null;
  img_md5: string | null;
  type: string | null;
};

export type DhgateUploadImgParams = {
  store_id: number;
  file: File | Blob;
  filename?: string;
};

/** POST /api/v1/common/utils/dhgate/tweakimg — 微调并上传 */
export type DhgateTweakImgPublic = {
  original: DhProductImgPublic;
  tweaked: DhProductImgPublic;
};

export type DhgateTweakImgParams = {
  store_id: number;
  img_url?: string | null;
  img_md5?: string | null;
  type?: string | null;
  file?: File | Blob | null;
  filename?: string;
};

/** @deprecated 使用 DhgateTweakImgPublic */
export type DhgateUploadImgPublic = DhgateTweakImgPublic;

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
  measure_id?: string | null;
  item_weight_range?: DhItemWeightRangePublic | null;
  shipping_model_id?: string | null;
  after_sale_template_id?: string | null;
  size_template_id?: string | null;
  short_desc1?: string | null;
  short_desc2?: string | null;
  short_desc3?: string | null;
  short_desc4?: string | null;
  short_desc5?: string | null;
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
  item_img_list: DhProductImgPublic[];
  sku_list: DhProductSkuPublic[];
  category: DhCategoryPublic | null;
  item_group_id?: string | null;
  attr_list?: DhProductSelectedAttrPublic[];
  /** 自定义规格（对应 dh.item.get itemSpecSelfDefList） */
  item_spec_self_def_list?: DhProductSpecSelfDefPublic[];
  item_wholesale_range_list?: DhItemWholesaleRangePublic[];
  item_inventory?: DhItemInventoryPublic | null;
  item_attr_group_list?: DhItemAttrGroupPublic[];
  item_shipto_setting_list?: DhItemShiptoSettingPublic[];
  item_custom_type_info?: DhItemCustomTypeInfoPublic | null;
};

/** 敦煌产品分组（与后端 DhProductGroupPublic 对齐） */
export type DhProductGroupPublic = {
  group_id: string;
  parent_group_id: string | null;
  group_name: string | null;
  group_en_name: string | null;
  remark: string | null;
  item_count: number;
  show_in_store: number | null;
  update_date: string | null;
  children?: DhProductGroupPublic[];
};

/** POST /api/v1/admin/stores/groups */
export type DhProductGroupListParams = {
  store_id: number;
  keyword?: string;
  page?: number;
  page_size?: number;
};

/** 供应商用户下拉项 */
export type SupplierUserOption = {
  id: number;
  username: string;
  nickname: string;
  role: string;
};

export type MissionStatus =
  | 'pending'
  | 'running'
  | 'finished'
  | 'marked_finished';

export type FissionStatus =
  | 'pending'
  | 'success'
  | 'failed'
  | 'marked_finished';

export type MissionPublic = {
  id: number;
  supplier_id: number;
  supplier_name?: string | null;
  title: string;
  description: string | null;
  status: MissionStatus;
  worker_id: number;
  worker_username: string;
  worker_nickname: string;
  created_by: number | null;
  creator_username: string | null;
  creator_nickname: string | null;
  created_at: string;
  updated_at: string;
};

export type MissionListParams = {
  supplier_id?: number;
  keyword?: string;
  page?: number;
  page_size?: number;
};

export type MissionCreateParams = {
  title: string;
  description?: string;
  worker_id: number;
  supplier_id?: number;
};

export type MissionUpdateParams = {
  id: number;
  title: string;
  description?: string;
  worker_id: number;
  supplier_id?: number;
};

export type MissionFissionDataDetailPublic = {
  id: number;
  mission_id: number;
  supplier_id: number;
  seed_product_id: number;
  fission_status: FissionStatus | string;
  update_json: Record<string, unknown>;
  raw_json: DhProductDetailPublic | null;
  seed_json: DhProductDetailPublic | null;
};

export type MissionFissionDataAddParams = {
  mission_id: number;
  seed_product_id: number;
  update_json: Record<string, unknown>;
  raw_json: DhProductDetailPublic;
  /** 加入时冻结的种子详情，供后续编辑按最初种子重算差异 */
  seed_json?: DhProductDetailPublic;
};

export type MissionFissionDataUpdateParams = {
  id: number;
  mission_id: number;
  update_json: Record<string, unknown>;
  raw_json: DhProductDetailPublic;
};

export type MissionFissionDataPublic = {
  id: number;
  mission_id: number;
  supplier_id: number;
  seed_product_id: number;
  store_id: number;
  store_name?: string | null;
  /** 原商品编码（种子商品） */
  seed_item_code?: string | null;
  item_code: string | null;
  site_id: string;
  cate_pub_id?: string | null;
  item_name?: string | null;
  main_image_url?: string | null;
  update_json: Record<string, unknown>;
  fission_status: FissionStatus;
  fission_msg: string | null;
  fission_at?: string | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

export type MissionLogPublic = {
  id: number;
  mission_id: number;
  operator_id: number;
  operator_username: string | null;
  operator_nickname: string | null;
  started_at: string;
  ended_at: string | null;
  success_count: number;
  fail_count: number;
  remark: string | null;
  created_at: string;
};
