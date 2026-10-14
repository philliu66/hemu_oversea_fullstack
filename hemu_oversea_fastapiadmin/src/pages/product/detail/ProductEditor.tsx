import {
  PageContainer,
  ProForm,
  ProFormCascader,
  ProFormDependency,
  ProFormList,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { history, useModel } from '@umijs/max';
import {
  App,
  Button,
  Card,
  Divider,
  Form,
  Input,
  Radio,
  Skeleton,
  Space,
  Spin,
  Typography,
} from 'antd';
import type { DefaultOptionType } from 'antd/es/cascader';
import React, {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import {
  DH_PRODUCT_STATE_LABEL,
  DH_PRODUCT_STATES,
  type DhProductStateCode,
} from '@/constants/product';
import { customAttrValueChanged } from '@/pages/mission/fission/attrDiff';
import {
  findItemGroupPath,
  toItemGroupCascaderOptions,
  withFallbackGroupOption,
} from '@/pages/product/itemGroupCascader';
import {
  createEmptyProductDetail,
  formatSyncState,
  isProductPageEditable,
  PRODUCT_LIST_PATH,
  productCreatePath,
  productEditPath,
  toCopyProductDetail,
  type ProductPageMode,
} from '@/pages/product/utils';
import {
  fetchDhCategoryAttrs,
  fetchDhCategoryPath,
  fetchDhCommissionRate,
} from '@/services/admin/categories';
import { fetchDhProductDetail } from '@/services/admin/products';
import {
  fetchStoreList,
  fetchStoreProductGroups,
} from '@/services/admin/stores';
import { lookupSkuAttrTemplates } from '@/services/admin/templates';
import type {
  DhCategoryAttrPublic,
  DhCategoryPublic,
  DhCommissionRatePublic,
  DhProductDetailPublic,
  DhProductSelectedAttrPublic,
  DhProductSkuPublic,
} from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import CategoryAttrsFields from './CategoryAttrsFields';
import CategorySelectField, {
  formatCategoryLabel,
  formatCategoryPathDisplay,
} from './CategorySelectField';
import './changedHighlight.css';
import {
  collectDistinctSkuBaseModels,
  REF_PRICING_CATE_ID,
} from './CommissionRateHint';
import PackageInfoFields from './PackageInfoFields';
import ProductImagesEditor from './ProductImagesEditor';
import ProductSpecSkuBlock from './ProductSpecSkuBlock';
import SaleInfoFields from './SaleInfoFields';
import TemplateInfoFields from './TemplateInfoFields';
import {
  DH_CUSTOM_PRODUCT_ATTR_ID,
  buildDetailFromForm,
  mergeManagedAttrsIntoList,
  nonSaleCategoryAttrs,
  priceProductAttrs,
  retainAttrsForCategory,
  selectedAttrsForCategoryIds,
  syncIsPriceAttrByCategory,
  toCustomAttrDrafts,
  toProductFormValues,
  type CustomAttrDraft,
  type ProductFormValues,
} from './productFormMapping';

const ITEM_NAME_MAX_LENGTH = 140;
const CHANGED_COLOR = '#cf1322';
const DH_CUSTOM_ATTR_MAX_COUNT = 20;
const DH_CUSTOM_ATTR_MAX_LENGTH = 40;

function formatProductState(state: string | null | undefined): string {
  const code = String(state || '').trim();
  if (!code) {
    return '-';
  }
  if ((DH_PRODUCT_STATES as readonly string[]).includes(code)) {
    return DH_PRODUCT_STATE_LABEL[code as DhProductStateCode];
  }
  return code;
}

function changedLabel(text: string, changed: boolean) {
  if (!changed) {
    return text;
  }
  return <span style={{ color: CHANGED_COLOR }}>{text}</span>;
}

function changedControlStyle(changed: boolean): React.CSSProperties {
  return changed ? { color: CHANGED_COLOR } : {};
}

/** 比较两份属性选择是否一致（用于多型号模板冲突检测） */
function attrListSignature(
  list: DhProductSelectedAttrPublic[] | undefined,
): string {
  const cloned = structuredClone(list || []) as DhProductSelectedAttrPublic[];
  cloned.sort((a, b) => String(a.attr_id).localeCompare(String(b.attr_id)));
  for (const attr of cloned) {
    const values = [...(attr.values || [])];
    values.sort((a, b) =>
      String(a.attr_val_id ?? '').localeCompare(String(b.attr_val_id ?? '')),
    );
    attr.values = values;
  }
  return JSON.stringify(cloned);
}

function pageTitle(mode: ProductPageMode): string {
  switch (mode) {
    case 'create':
      return '新建商品';
    case 'copy':
      return '复制商品';
    case 'edit':
      return '编辑商品';
    default:
      return '商品详情';
  }
}

function filterItemGroupOption(inputValue: string, path: DefaultOptionType[]) {
  const keyword = inputValue.trim().toLowerCase();
  if (!keyword) {
    return true;
  }
  return path.some((option) => {
    const label = String(option.label ?? '').toLowerCase();
    const value = String(option.value ?? '').toLowerCase();
    return label.includes(keyword) || value.includes(keyword);
  });
}

/** 商品编辑必填字段（新建 / 编辑 / 裂变共用） */
export const PRODUCT_EDITOR_REQUIRED_FIELDS = [
  'store_id',
  'cate_pub_id',
  'item_name',
  'item_img_list',
  'after_sale_template_id',
  'shipping_model_id',
] as const;

export type ProductEditorHandle = {
  getBaseline: () => DhProductDetailPublic | null;
  getSnapshot: () => DhProductDetailPublic | null;
  isReady: () => boolean;
  /** 校验必填项；失败时 reject 并展示字段错误 */
  validate: () => Promise<void>;
};

export type ProductEditorProps = {
  mode?: ProductPageMode;
  productId?: number;
  fromId?: number;
  initialDetail?: DhProductDetailPublic;
  readOnly?: boolean;
  changedKeys?: string[];
  changedAttrList?: DhProductSelectedAttrPublic[];
  embedded?: boolean;
  /**
   * 切换产品分类时，按当前商品 SKU 基型号 + 分类查询属性模板并覆盖选择。
   * 用于裂变「手动添加」第二步。
   */
  applySkuAttrTemplateOnCategoryChange?: boolean;
  /**
   * 加载后清空产品标题输入，将原种子标题作为 placeholder（提醒用户重新填写）。
   * 用于裂变「手动添加」第二步；baseline 仍保留原标题供 diff。
   */
  seedTitleAsItemNamePlaceholder?: boolean;
};

export const ProductEditor = forwardRef<
  ProductEditorHandle,
  ProductEditorProps
>(function ProductEditor(
  {
    mode: modeProp,
    productId,
    fromId,
    readOnly: readOnlyProp,
    initialDetail,
    changedKeys = [],
    changedAttrList = [],
    embedded = false,
    applySkuAttrTemplateOnCategoryChange = false,
    seedTitleAsItemNamePlaceholder = false,
  },
  ref,
) {
  const { message, modal } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const supplierId = initialState?.currentUser?.supplier_id;
  const [itemNamePlaceholder, setItemNamePlaceholder] =
    useState('请输入产品标题');
  const mode: ProductPageMode =
    modeProp ??
    (readOnlyProp
      ? 'view'
      : productId || initialDetail
        ? 'edit'
        : 'create');
  const editable = readOnlyProp === true ? false : isProductPageEditable(mode);
  const readOnly = !editable;
  const sourceProductId = mode === 'copy' ? fromId : productId;
  const formInstanceKey =
    mode === 'create'
      ? 'create'
      : mode === 'copy'
        ? `copy-${fromId}`
        : initialDetail
          ? `snapshot-${initialDetail.id}`
          : `${mode}-${productId}`;
  const [form] = Form.useForm<ProductFormValues>();
  const changedKeySet = new Set(changedKeys);
  const isChanged = (key: string) => changedKeySet.has(key);
  const changedCategoryAttrIds = changedAttrList
    .map((item) => String(item.attr_id))
    .filter((attrId) => attrId !== DH_CUSTOM_PRODUCT_ATTR_ID);
  const changedCustomValues = changedAttrList.find(
    (item) => String(item.attr_id) === DH_CUSTOM_PRODUCT_ATTR_ID,
  )?.values;

  const [baseDetail, setBaseDetail] = useState<DhProductDetailPublic>();
  const baselineRef = useRef<DhProductDetailPublic | null>(null);
  const [pickedCategory, setPickedCategory] = useState<DhCategoryPublic | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [categoryPath, setCategoryPath] = useState<string>();
  const [categoryAttrs, setCategoryAttrs] = useState<DhCategoryAttrPublic[]>(
    [],
  );
  const [categoryAttrsLoading, setCategoryAttrsLoading] = useState(false);
  const [commissionRate, setCommissionRate] =
    useState<DhCommissionRatePublic | null>(null);
  const [commissionRateLoading, setCommissionRateLoading] = useState(false);
  const categoryAttrsReqRef = useRef(0);
  const commissionRateReqRef = useRef(0);
  const baselineItemGroupIdRef = useRef<string | null | undefined>(undefined);

  const displayCategory = pickedCategory ?? baseDetail?.category ?? null;
  /** 规格卡片标红：仅定价属性变更，不含普通类目属性 */
  const priceAttrIdSetFromDetail = new Set(
    priceProductAttrs(baseDetail?.attr_list).map((item) => String(item.attr_id)),
  );
  const hasChangedPriceAttr = changedAttrList.some((item) => {
    const attrId = String(item.attr_id);
    if (attrId === DH_CUSTOM_PRODUCT_ATTR_ID) {
      return false;
    }
    return (
      String(item.is_price_attr) === '1' || priceAttrIdSetFromDetail.has(attrId)
    );
  });
  const specCardChanged =
    isChanged('sku_list') ||
    isChanged('item_spec_self_def_list') ||
    hasChangedPriceAttr;

  useImperativeHandle(
    ref,
    () => ({
      getBaseline: () => baselineRef.current,
      getSnapshot: () => {
        if (!baselineRef.current) {
          return null;
        }
        return buildDetailFromForm(
          baselineRef.current,
          form.getFieldsValue(true),
          pickedCategory ?? baselineRef.current.category,
        );
      },
      isReady: () => Boolean(baselineRef.current) && !loading,
      validate: async () => {
        await form.validateFields([...PRODUCT_EDITOR_REQUIRED_FIELDS]);
      },
    }),
    [form, loading, pickedCategory],
  );

  const loadCategoryAttrs = useCallback(async (categoryId: number) => {
    const reqId = categoryAttrsReqRef.current + 1;
    categoryAttrsReqRef.current = reqId;
    setCategoryAttrsLoading(true);
    setCategoryAttrs([]);
    try {
      const attrs = await fetchDhCategoryAttrs(categoryId);
      if (categoryAttrsReqRef.current !== reqId) {
        return undefined;
      }
      const list = attrs.attrs || [];
      setCategoryAttrs(list);
      return list;
    } catch {
      if (categoryAttrsReqRef.current !== reqId) {
        return undefined;
      }
      setCategoryAttrs([]);
      return undefined;
    } finally {
      if (categoryAttrsReqRef.current === reqId) {
        setCategoryAttrsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setBaseDetail(undefined);
    baselineRef.current = null;
    setPickedCategory(null);
    baselineItemGroupIdRef.current = undefined;
    setCategoryPath(undefined);
    setCategoryAttrs([]);
    setCategoryAttrsLoading(false);
    categoryAttrsReqRef.current += 1;
    void (async () => {
      try {
        let data: DhProductDetailPublic | undefined;
        if (initialDetail) {
          data = initialDetail;
        } else if (mode === 'create') {
          data = createEmptyProductDetail();
        } else if (sourceProductId) {
          const fetched = await fetchDhProductDetail(sourceProductId);
          data = mode === 'copy' ? toCopyProductDetail(fetched) : fetched;
        }

        if (!data) {
          throw new Error('加载商品详情失败');
        }
        if (cancelled) {
          return;
        }

        const baseline = structuredClone(data);
        baselineRef.current = baseline;
        baselineItemGroupIdRef.current = data.item_group_id;
        setBaseDetail(data);
        setPickedCategory(data.category);
        const formValues = toProductFormValues(data);
        const seedTitle = (data.item_name || '').trim();
        if (seedTitleAsItemNamePlaceholder) {
          formValues.item_name = '';
          setItemNamePlaceholder(seedTitle || '请输入产品标题');
        } else {
          setItemNamePlaceholder('请输入产品标题');
        }
        form.setFieldsValue(formValues);
        setLoading(false);

        if (data.category?.id) {
          const categoryId = data.category.id;
          void loadCategoryAttrs(categoryId).then((attrs) => {
            if (cancelled || attrs === undefined) {
              return;
            }
            const prev = form.getFieldValue('attr_list') as
              | DhProductSelectedAttrPublic[]
              | undefined;
            form.setFieldsValue({
              attr_list: syncIsPriceAttrByCategory(prev, attrs),
            });
          });
          void (async () => {
            try {
              const pathData = await fetchDhCategoryPath(categoryId);
              if (cancelled) {
                return;
              }
              setCategoryPath(formatCategoryPathDisplay(pathData));
              form.setFieldsValue({
                category_path: pathData.path_items.map(
                  (item) => item.cate_pub_id,
                ),
              });
            } catch (pathError) {
              if (cancelled) {
                return;
              }
              setCategoryPath(
                data.category ? formatCategoryLabel(data.category) : undefined,
              );
              const fallbackId =
                data.cate_pub_id || data.category?.cate_pub_id;
              form.setFieldsValue({
                category_path: fallbackId ? [fallbackId] : undefined,
              });
              message.error(
                pathError instanceof Error
                  ? pathError.message
                  : '获取分类全路径失败',
              );
            }
          })();
        } else {
          setCategoryPath(undefined);
          setCategoryAttrs([]);
          setCategoryAttrsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          setBaseDetail(undefined);
          baselineRef.current = null;
          setPickedCategory(null);
          setCategoryAttrs([]);
          setCategoryAttrsLoading(false);
          message.error(
            error instanceof Error ? error.message : '加载商品详情失败',
          );
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
      categoryAttrsReqRef.current += 1;
    };
  }, [
    form,
    initialDetail,
    loadCategoryAttrs,
    message,
    mode,
    seedTitleAsItemNamePlaceholder,
    sourceProductId,
  ]);

  useEffect(() => {
    const reqId = commissionRateReqRef.current + 1;
    commissionRateReqRef.current = reqId;
    setCommissionRateLoading(true);
    setCommissionRate(null);
    void fetchDhCommissionRate(REF_PRICING_CATE_ID, { skipErrorHandler: true })
      .then((data) => {
        if (commissionRateReqRef.current === reqId) {
          setCommissionRate(data);
        }
      })
      .catch(() => {
        if (commissionRateReqRef.current === reqId) {
          setCommissionRate(null);
        }
      })
      .finally(() => {
        if (commissionRateReqRef.current === reqId) {
          setCommissionRateLoading(false);
        }
      });
  }, []);

  const handleCategoryPick = useCallback(
    (picked: DhCategoryPublic) => {
      void (async () => {
        try {
          const pathData = await fetchDhCategoryPath(picked.id);
          setCategoryPath(formatCategoryPathDisplay(pathData));
          const selectedCategory =
            pathData.path_items[pathData.path_items.length - 1] ?? picked;
          setPickedCategory(selectedCategory);
          form.setFieldsValue({
            category_path: pathData.path_items.map((item) => item.cate_pub_id),
            cate_pub_id: selectedCategory.cate_pub_id,
          });
          const nextCategoryAttrs = await loadCategoryAttrs(picked.id);
          // 拉取失败时不改 attr_list，避免误清空
          if (nextCategoryAttrs === undefined) {
            return;
          }

          const prev = form.getFieldValue('attr_list') as
            | DhProductSelectedAttrPublic[]
            | undefined;
          const allowedIds = nextCategoryAttrs.map((item) =>
            String(item.attr_id),
          );

          // 裂变手动添加：按基型号查属性模板，决定覆盖 / 提示 / 冲突
          if (applySkuAttrTemplateOnCategoryChange && !readOnly) {
            const skuList = (form.getFieldValue('sku_list') ||
              []) as DhProductSkuPublic[];
            const baseModels = collectDistinctSkuBaseModels(skuList);
            if (baseModels.length > 0 && selectedCategory.cate_pub_id) {
              try {
                const lookup = await lookupSkuAttrTemplates({
                  cate_pub_id: selectedCategory.cate_pub_id,
                  sku_codes: baseModels,
                });
                const foundItems = (lookup.items || []).filter(
                  (item) => item.found,
                );
                const missingModels = (lookup.items || [])
                  .filter((item) => !item.found)
                  .map((item) => item.sku_code);

                if (foundItems.length === 0) {
                  message.warning(
                    `${baseModels.join('、')}型号没有对应的属性模板`,
                  );
                  // 无模板：不清空原先属性选择
                  return;
                }

                const signatures = foundItems.map((item) =>
                  attrListSignature(
                    (item.raw_json?.attr_list ||
                      []) as DhProductSelectedAttrPublic[],
                  ),
                );
                const uniqueSignatures = new Set(signatures);
                if (uniqueSignatures.size > 1) {
                  modal.warning({
                    title: '属性模板冲突',
                    content:
                      '该商品存在多个不同的产品型号且分类下属性选择不一致',
                  });
                  // 冲突：不覆盖原先数据
                  return;
                }

                if (missingModels.length > 0) {
                  message.warning(
                    `${missingModels.join('、')}型号没有对应的属性模板`,
                  );
                }

                const templateAttrList = (foundItems[0].raw_json?.attr_list ||
                  []) as DhProductSelectedAttrPublic[];
                // 有模板：清空原选择，用模板覆盖（仅保留新类目相关 + 自定义）
                form.setFieldsValue({
                  attr_list: syncIsPriceAttrByCategory(
                    retainAttrsForCategory(templateAttrList, allowedIds),
                    nextCategoryAttrs,
                  ),
                  customAttrs: toCustomAttrDrafts(templateAttrList),
                });
                return;
              } catch (lookupError) {
                message.error(
                  lookupError instanceof Error
                    ? lookupError.message
                    : '查询属性模板失败',
                );
                // 查询失败时回退为常规收敛，避免卡在旧类目属性
              }
            }
          }

          form.setFieldsValue({
            attr_list: syncIsPriceAttrByCategory(
              retainAttrsForCategory(prev, allowedIds),
              nextCategoryAttrs,
            ),
          });
        } catch (error) {
          message.error(
            error instanceof Error ? error.message : '获取分类全路径失败',
          );
        }
      })();
    },
    [
      applySkuAttrTemplateOnCategoryChange,
      form,
      loadCategoryAttrs,
      message,
      modal,
      readOnly,
    ],
  );

  const routeInvalid =
    !embedded &&
    ((mode === 'view' || mode === 'edit') && !productId
      ? true
      : mode === 'copy' && !fromId);

  if (routeInvalid) {
    return (
      <PageContainer
        title={false}
        onBack={() => history.push(PRODUCT_LIST_PATH)}
      >
        <Card>{'商品 ID 无效'}</Card>
      </PageContainer>
    );
  }

  const showSyncMeta = mode === 'view' || mode === 'edit';

  const content = (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <ProForm<ProductFormValues>
        key={formInstanceKey}
        form={form}
        disabled={readOnly}
        submitter={false}
        layout="horizontal"
        labelAlign="left"
        labelCol={{ flex: '110px' }}
        wrapperCol={{ flex: 1 }}
        scrollToFirstError
        onValuesChange={(changedValues) => {
          if (readOnly) {
            return;
          }
          if ('store_id' in changedValues) {
            baselineItemGroupIdRef.current = null;
            form.setFieldsValue({
              item_group_path: undefined,
              after_sale_template_id: null,
              shipping_model_id: null,
            });
          }
        }}
      >
        <Card title={'基本信息'}>
          <Spin spinning={loading}>
            <ProFormSelect
              name="store_id"
              label={changedLabel('店铺名称', isChanged('store_id'))}
              showSearch
              debounceTime={300}
              params={{ supplierId }}
              rules={[{ required: true, message: '请选择店铺名称' }]}
              request={async () => {
                if (!supplierId) {
                  return [];
                }
                const data = await fetchStoreList({
                  supplier_id: supplierId,
                  page: 1,
                  page_size: 100,
                });
                return data.items.map((store) => ({
                  label: store.name,
                  value: store.id,
                }));
              }}
              fieldProps={{
                style: {
                  maxWidth: 360,
                  ...changedControlStyle(isChanged('store_id')),
                },
              }}
            />
            <Form.Item
              label={changedLabel('产品分类', isChanged('cate_pub_id'))}
              name="cate_pub_id"
              rules={[{ required: true, message: '请选择产品分类' }]}
            >
              <CategorySelectField
                category={displayCategory}
                pathDisplay={categoryPath}
                disabled={readOnly}
                changed={isChanged('cate_pub_id')}
                onPick={handleCategoryPick}
              />
            </Form.Item>
          </Spin>
        </Card>

        <Card
          title={changedLabel('商品属性', isChanged('attr_list'))}
          style={{ marginTop: 16 }}
        >
          <Typography.Text strong style={{ display: 'block', marginBottom: 12 }}>
            {'类目属性'}
          </Typography.Text>
          {categoryAttrsLoading ? (
            <Skeleton active paragraph={{ rows: 8 }} />
          ) : (
            <ProFormDependency name={['attr_list']}>
              {({ attr_list }) => {
                // 按类目定义 sale_attr 分流；与商品规格区块统一
                const normalCategoryAttrs = nonSaleCategoryAttrs(categoryAttrs);
                const normalSelectedAttrs = selectedAttrsForCategoryIds(
                  attr_list,
                  normalCategoryAttrs.map((item) => String(item.attr_id)),
                );
                if (normalCategoryAttrs.length === 0) {
                  return !loading ? (
                    <Typography.Text type="secondary">
                      {'暂无类目属性'}
                    </Typography.Text>
                  ) : null;
                }
                return (
                  <CategoryAttrsFields
                    attrs={normalCategoryAttrs}
                    selectedAttrs={normalSelectedAttrs}
                    disabled={readOnly}
                    changedAttrIds={changedCategoryAttrIds}
                    onSelectedAttrsChange={
                      readOnly
                        ? undefined
                        : (nextSelected) => {
                            const managedIds = normalCategoryAttrs.map((item) =>
                              String(item.attr_id),
                            );
                            const cleared = nextSelected.map((item) => ({
                              ...item,
                              is_price_attr: '0',
                            }));
                            const prev = form.getFieldValue('attr_list') as
                              | DhProductSelectedAttrPublic[]
                              | undefined;
                            form.setFieldsValue({
                              attr_list: mergeManagedAttrsIntoList(
                                prev,
                                managedIds,
                                cleared,
                              ),
                            });
                          }
                    }
                  />
                );
              }}
            </ProFormDependency>
          )}
          <Divider />
          <Typography.Text
            strong
            style={{
              display: 'block',
              marginBottom: 8,
              color: changedCustomValues?.length ? CHANGED_COLOR : undefined,
            }}
          >
            {'自定义属性'}
          </Typography.Text>
          <ProFormList
            name="customAttrs"
            copyIconProps={false}
            deleteIconProps={
              readOnly
                ? false
                : {
                    tooltipText: '删除',
                  }
            }
            creatorButtonProps={
              readOnly
                ? false
                : {
                    creatorButtonText: '新增属性',
                    type: 'dashed',
                    style: { width: '100%', maxWidth: 720 },
                  }
            }
            max={DH_CUSTOM_ATTR_MAX_COUNT}
            creatorRecord={() => ({
              key: `custom-new-${Date.now()}`,
              attr_val_id: null,
              attr_name: '',
              content: '',
            })}
            itemRender={({ listDom, action }, meta) => {
              const record =
                (meta?.record as CustomAttrDraft | undefined) || {};
              const rowChanged = customAttrValueChanged(
                changedCustomValues,
                record,
              );
              return (
                <div
                  className={rowChanged ? 'hm-changed-control' : undefined}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    marginBottom: 8,
                    color: rowChanged ? CHANGED_COLOR : undefined,
                  }}
                >
                  {listDom}
                  {readOnly ? null : action}
                </div>
              );
            }}
          >
            <Space size={8} wrap align="center">
              <ProFormText name="key" hidden />
              <ProFormText name="attr_val_id" hidden />
              <ProFormText
                name="attr_name"
                placeholder={'请输入属性名'}
                fieldProps={{
                  maxLength: DH_CUSTOM_ATTR_MAX_LENGTH,
                  allowClear: true,
                  style: { width: 220 },
                }}
                formItemProps={{ style: { marginBottom: 0 } }}
              />
              <ProFormText
                name="content"
                placeholder={'请输入属性值'}
                fieldProps={{
                  maxLength: DH_CUSTOM_ATTR_MAX_LENGTH,
                  allowClear: true,
                  style: { width: 320 },
                }}
                formItemProps={{ style: { marginBottom: 0 } }}
              />
            </Space>
          </ProFormList>
        </Card>

        <Card title={'产品信息'} style={{ marginTop: 16 }}>
          <Spin spinning={loading}>
          <Form.Item
            name="item_name"
            label={changedLabel('产品标题', isChanged('item_name'))}
            rules={[
              {
                required: true,
                whitespace: true,
                message: '请输入产品标题',
              },
              {
                max: ITEM_NAME_MAX_LENGTH,
                message: `产品标题最多 ${ITEM_NAME_MAX_LENGTH} 个字符`,
              },
            ]}
          >
            <Input
              maxLength={ITEM_NAME_MAX_LENGTH}
              allowClear
              disabled={readOnly}
              style={changedControlStyle(isChanged('item_name'))}
              placeholder={itemNamePlaceholder}
            />
          </Form.Item>
          <Form.Item
            label={changedLabel(
              '关键词',
              isChanged('key_word1') ||
                isChanged('key_word2') ||
                isChanged('key_word3'),
            )}
          >
            <Space size={12} wrap>
              <Form.Item name="key_word1" noStyle>
                <Input
                  allowClear
                  disabled={readOnly}
                  style={{
                    width: 240,
                    ...changedControlStyle(isChanged('key_word1')),
                  }}
                />
              </Form.Item>
              <Form.Item name="key_word2" noStyle>
                <Input
                  allowClear
                  disabled={readOnly}
                  style={{
                    width: 240,
                    ...changedControlStyle(isChanged('key_word2')),
                  }}
                />
              </Form.Item>
              <Form.Item name="key_word3" noStyle>
                <Input
                  allowClear
                  disabled={readOnly}
                  style={{
                    width: 240,
                    ...changedControlStyle(isChanged('key_word3')),
                  }}
                />
              </Form.Item>
            </Space>
          </Form.Item>

          <ProFormCascader
            name="item_group_path"
            label={changedLabel('产品分组', isChanged('item_group_id'))}
            disabled={readOnly}
            placeholder={'请选择产品分组'}
            dependencies={['store_id']}
            fieldProps={{
              changeOnSelect: true,
              allowClear: true,
              showSearch: { filter: filterItemGroupOption },
              style: {
                maxWidth: 480,
                width: '100%',
                ...changedControlStyle(isChanged('item_group_id')),
              },
            }}
            request={async (params) => {
              const storeId = params.store_id as number | undefined;
              if (!storeId) {
                return [];
              }
              try {
                const data = await fetchStoreProductGroups({
                  store_id: storeId,
                });
                const options = toItemGroupCascaderOptions(data.items || []);
                const groupId = baselineItemGroupIdRef.current;
                const withFallback = withFallbackGroupOption(options, groupId);
                const current = form.getFieldValue('item_group_path') as
                  | string[]
                  | undefined;
                if (
                  groupId &&
                  (!Array.isArray(current) || current.length === 0)
                ) {
                  const path = findItemGroupPath(withFallback, groupId);
                  if (path?.length) {
                    form.setFieldsValue({ item_group_path: path });
                  }
                }
                return withFallback;
              } catch {
                return [];
              }
            }}
          />

          <Form.Item name="issample" label={'商品分级管理'}>
            <Radio.Group disabled={readOnly}>
              <Radio value="3">{'非成人属性'}</Radio>
              <Radio value="2">{'成人属性'}</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item name="vaild_day" label={'产品有效期'}>
            <Radio.Group disabled={readOnly}>
              <Radio value="90">{'90天'}</Radio>
              <Radio value="30">{'30天'}</Radio>
              <Radio value="14">{'14天'}</Radio>
            </Radio.Group>
          </Form.Item>
          {showSyncMeta ? (
            <>
              <Form.Item label={'商品状态'}>
                {formatProductState(baseDetail?.state)}
              </Form.Item>
              <Form.Item label={'同步状态'}>
                {formatSyncState(baseDetail?.sync_state, '成功', '失败')}
              </Form.Item>
              <Form.Item label={'同步时间'}>
                {formatDateTime(baseDetail?.last_synced_at)}
              </Form.Item>
            </>
          ) : null}
          </Spin>
        </Card>

        <Card title={'销售信息'} style={{ marginTop: 16 }}>
          <Spin spinning={loading}>
            <SaleInfoFields disabled={readOnly} />
          </Spin>
        </Card>

        <Card
          title={changedLabel('商品图片', isChanged('item_img_list'))}
          style={{ marginTop: 16 }}
        >
          <Spin spinning={loading}>
            <ProFormDependency name={['store_id']}>
              {({ store_id }) => (
                <Form.Item
                  name="item_img_list"
                  valuePropName="images"
                  trigger="onChange"
                  rules={[
                    {
                      validator: async (_, value) => {
                        const list = Array.isArray(value) ? value : [];
                        if (list.length === 0) {
                          throw new Error('请上传商品图片');
                        }
                      },
                    },
                  ]}
                >
                  <ProductImagesEditor
                    disabled={readOnly}
                    storeId={store_id || undefined}
                    alt={baseDetail?.item_code}
                  />
                </Form.Item>
              )}
            </ProFormDependency>
          </Spin>
        </Card>

        <Card
          title={changedLabel('商品规格', specCardChanged)}
          style={{ marginTop: 16 }}
        >
          <ProductSpecSkuBlock
            readOnly={readOnly}
            categoryAttrsLoading={categoryAttrsLoading}
            categoryAttrs={categoryAttrs}
            changedCategoryAttrIds={changedCategoryAttrIds}
            categoryPath={categoryPath}
            supplierId={supplierId}
            itemCode={baseDetail?.item_code}
            commissionLoading={commissionRateLoading}
            commissionData={commissionRate}
          />
        </Card>

        {baseDetail?.html_content ? (
          <Card
            title={changedLabel('详情描述', isChanged('html_content'))}
            style={{ marginTop: 16 }}
          >
            <iframe
              title={'详情描述'}
              srcDoc={baseDetail.html_content}
              sandbox=""
              style={{
                width: '100%',
                minHeight: 360,
                maxHeight: 480,
                border: isChanged('html_content')
                  ? `1px solid ${CHANGED_COLOR}`
                  : 'none',
                background: '#fff',
              }}
            />
          </Card>
        ) : null}

        <Card
          title={changedLabel(
            '包装信息',
            isChanged('gross_weight') ||
              isChanged('length') ||
              isChanged('width') ||
              isChanged('height') ||
              isChanged('item_weight_range'),
          )}
          style={{ marginTop: 16 }}
        >
          <Spin spinning={loading}>
            <PackageInfoFields disabled={readOnly} />
          </Spin>
        </Card>

        <Card title={'模板信息'} style={{ marginTop: 16 }}>
          <Spin spinning={loading}>
            <TemplateInfoFields
              disabled={readOnly}
              afterSaleLabel={changedLabel(
                '售后模板',
                isChanged('after_sale_template_id'),
              )}
              shippingLabel={changedLabel(
                '物流模板',
                isChanged('shipping_model_id'),
              )}
              afterSaleChanged={isChanged('after_sale_template_id')}
              shippingChanged={isChanged('shipping_model_id')}
              changedControlStyle={changedControlStyle(true)}
            />
          </Spin>
        </Card>
      </ProForm>
    </Space>
  );

  if (embedded) {
    return content;
  }

  return (
    <PageContainer
      title={pageTitle(mode)}
      onBack={() => history.push(PRODUCT_LIST_PATH)}
      extra={
        mode === 'view' && productId ? (
          <Space wrap>
            <Button
              type="primary"
              onClick={() => history.push(productEditPath(productId))}
            >
              {'编辑'}
            </Button>
            <Button
              onClick={() =>
                history.push(productCreatePath({ from: productId }))
              }
            >
              {'复制'}
            </Button>
          </Space>
        ) : undefined
      }
    >
      {content}
    </PageContainer>
  );
});

export default ProductEditor;
