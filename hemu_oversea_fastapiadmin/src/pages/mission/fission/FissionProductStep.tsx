import {
  ProForm,
  ProFormList,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { useIntl, useModel } from '@umijs/max';
import {
  App,
  Card,
  Cascader,
  Divider,
  Form,
  Input,
  Select,
  Space,
  Typography,
} from 'antd';
import type { CascaderProps, DefaultOptionType } from 'antd/es/cascader';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  DH_PRODUCT_STATE_LABEL,
  DH_PRODUCT_STATES,
  type DhProductStateCode,
} from '@/constants/product';
import CategoryAttrsFields from '@/pages/product/detail/CategoryAttrsFields';
import ProductImagesEditor from '@/pages/product/detail/ProductImagesEditor';
import SpecAttrsFields from '@/pages/product/detail/SpecAttrsFields';
import SpecSkuTable from '@/pages/product/detail/SpecSkuTable';
import { formatSyncState } from '@/pages/product/utils';
import {
  findItemGroupPath,
  resolveItemGroupLabels,
  toItemGroupCascaderOption,
  type ItemGroupCascaderOption,
} from '@/pages/product/itemGroupCascader';
import {
  fetchDhCategories,
  fetchDhCategoryAttrs,
  fetchDhCategoryPath,
} from '@/services/admin/categories';
import {
  fetchDhProductDetail,
} from '@/services/admin/products';
import {
  fetchStoreAftersaleTemplates,
  fetchStoreList,
  fetchStoreProductGroups,
  fetchStoreShippingTemplates,
} from '@/services/admin/stores';
import type {
  DhCategoryAttrPublic,
  DhCategoryPathPublic,
  DhCategoryPublic,
  DhProductDetailPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';
import { customAttrValueChanged } from './attrDiff';
import { formatDateTime } from '@/utils/datetime';
import './changedHighlight.css';

const ITEM_NAME_MAX_LENGTH = 140;
const CHANGED_COLOR = '#cf1322';
const DH_CUSTOM_PRODUCT_ATTR_ID = '11';
const DH_CUSTOM_ATTR_MAX_COUNT = 20;
const DH_CUSTOM_ATTR_MAX_LENGTH = 40;

type ProductFormValues = {
  store_id?: number;
  category_path?: string[];
  item_name?: string;
  key_word1?: string;
  key_word2?: string;
  key_word3?: string;
  item_group_path?: string[];
  customAttrs?: CustomAttrDraft[];
};

type CustomAttrDraft = {
  key: string;
  attr_val_id: string | null;
  attr_name: string;
  content: string;
};

type CategoryOption = DefaultOptionType & {
  value: string;
  label: string;
  categoryId: number;
  isLeaf?: boolean;
  loading?: boolean;
  children?: CategoryOption[];
};

function isCustomProductAttr(attr: DhProductSelectedAttrPublic) {
  return String(attr.attr_id) === DH_CUSTOM_PRODUCT_ATTR_ID;
}

function isPriceProductAttr(attr: DhProductSelectedAttrPublic) {
  return String(attr.is_price_attr) === '1';
}

function categoryProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return (list || []).filter((item) => !isCustomProductAttr(item));
}

function priceProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return categoryProductAttrs(list).filter(isPriceProductAttr);
}

function nonPriceProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return categoryProductAttrs(list).filter((item) => !isPriceProductAttr(item));
}

/** 用本组件管理的属性子集替换 attr_list 中对应项，其它属性保留 */
function mergeManagedAttrsIntoList(
  list: DhProductSelectedAttrPublic[] | undefined,
  managedAttrIds: Iterable<string>,
  nextManaged: DhProductSelectedAttrPublic[],
): DhProductSelectedAttrPublic[] {
  const managedIdSet = new Set(
    [...managedAttrIds].map((id) => String(id).trim()).filter(Boolean),
  );
  const others = (list || []).filter(
    (item) => !managedIdSet.has(String(item.attr_id)),
  );
  return [...others, ...nextManaged];
}

/** 写入 / 覆盖指定属性值的 pic_url */
function patchAttrValuePic(
  list: DhProductSelectedAttrPublic[] | undefined,
  attrId: string,
  attrValId: string,
  picUrl: string | null,
): DhProductSelectedAttrPublic[] {
  const source = list || [];
  let foundAttr = false;
  const next = source.map((attr) => {
    if (String(attr.attr_id) !== String(attrId)) {
      return attr;
    }
    foundAttr = true;
    let foundVal = false;
    const values = (attr.values || []).map((item) => {
      if (String(item.attr_val_id) !== String(attrValId)) {
        return item;
      }
      foundVal = true;
      return { ...item, pic_url: picUrl };
    });
    if (!foundVal) {
      values.push({
        attr_val_id: attrValId,
        attr_name: attr.attr_name,
        attr_name_cn: attr.attr_name_cn,
        line_attrval_name: null,
        line_attrval_name_cn: null,
        pic_url: picUrl,
      });
    }
    return { ...attr, values };
  });
  if (!foundAttr) {
    next.push({
      attr_id: attrId,
      attr_name: null,
      attr_name_cn: null,
      is_price_attr: '1',
      values: [
        {
          attr_val_id: attrValId,
          attr_name: null,
          attr_name_cn: null,
          line_attrval_name: null,
          line_attrval_name_cn: null,
          pic_url: picUrl,
        },
      ],
    });
  }
  return next;
}

function toCustomAttrDrafts(
  list?: DhProductSelectedAttrPublic[],
): CustomAttrDraft[] {
  return (list || [])
    .filter(isCustomProductAttr)
    .flatMap((item) => item.values || [])
    .map((item, index) => ({
      key: item.attr_val_id || `custom-${index}`,
      attr_val_id: item.attr_val_id ?? null,
      attr_name: (item.attr_name_cn || item.attr_name || '').trim(),
      content: (
        item.line_attrval_name_cn ||
        item.line_attrval_name ||
        ''
      ).trim(),
    }));
}

function applyCustomAttrDraftsToAttrList(
  list: DhProductSelectedAttrPublic[] | undefined,
  drafts: CustomAttrDraft[],
): DhProductSelectedAttrPublic[] {
  const others = (list || []).filter((item) => !isCustomProductAttr(item));
  const values = drafts
    .map((item, index) => ({
      attr_id: DH_CUSTOM_PRODUCT_ATTR_ID,
      attr_val_id: item.attr_val_id || String(index + 1),
      attr_name: (item.attr_name || '').trim() || null,
      attr_name_cn: null,
      line_attrval_name: (item.content || '').trim() || null,
      line_attrval_name_cn: null,
      pic_url: null,
    }))
    .filter((item) => item.attr_name || item.line_attrval_name);
  if (!values.length) {
    return others;
  }
  return [
    ...others,
    {
      attr_id: DH_CUSTOM_PRODUCT_ATTR_ID,
      attr_name: null,
      attr_name_cn: null,
      values,
    },
  ];
}

function normalizeCustomAttrDrafts(
  drafts: CustomAttrDraft[] | undefined,
): CustomAttrDraft[] {
  return (drafts || []).map((item, index) => ({
    key: item?.key || `custom-${index}-${Date.now()}`,
    attr_val_id: item?.attr_val_id ?? null,
    attr_name: item?.attr_name ?? '',
    content: item?.content ?? '',
  }));
}

function formatCategoryLabel(category: DhCategoryPublic): string {
  const cn = category.pub_name_cn?.trim();
  const en = category.pub_name?.trim();
  if (cn && en && cn !== en) {
    return `${cn}(${en})`;
  }
  return cn || en || category.cate_pub_id;
}

function formatCategoryPathDisplay(path: DhCategoryPathPublic): string {
  if (path.path_items?.length) {
    return path.path_items.map(formatCategoryLabel).join('/');
  }
  return path.path_name.replaceAll(' > ', '/');
}

function toCascaderOption(item: DhCategoryPublic): CategoryOption {
  return {
    value: item.cate_pub_id,
    label: formatCategoryLabel(item),
    categoryId: item.id,
    isLeaf: item.is_leaf,
  };
}

function updateCascaderChildren(
  list: CategoryOption[],
  targetValue: string,
  children: CategoryOption[],
): CategoryOption[] {
  return list.map((node) => {
    if (node.value === targetValue) {
      return {
        ...node,
        loading: false,
        children,
        isLeaf: children.length === 0 ? true : node.isLeaf,
      };
    }
    if (node.children?.length) {
      return {
        ...node,
        children: updateCascaderChildren(node.children, targetValue, children),
      };
    }
    return node;
  });
}

async function loadCascaderOptionsAlongPath(
  pathItems: DhCategoryPublic[],
): Promise<CategoryOption[]> {
  const roots = await fetchDhCategories({});
  let options = roots.map(toCascaderOption);
  for (let i = 0; i < pathItems.length - 1; i += 1) {
    const parentPubId = pathItems[i].cate_pub_id;
    const children = await fetchDhCategories({ parent_id: parentPubId });
    options = updateCascaderChildren(
      options,
      parentPubId,
      children.map(toCascaderOption),
    );
  }
  return options;
}

function formatProductState(
  state: string | null | undefined,
  t: (id: string, defaultMessage: string) => string,
): string {
  const code = String(state || '').trim();
  if (!code) {
    return '-';
  }
  if ((DH_PRODUCT_STATES as readonly string[]).includes(code)) {
    return t(
      `pages.product.list.state.${code}`,
      DH_PRODUCT_STATE_LABEL[code as DhProductStateCode],
    );
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

function textOrNull(value: string | null | undefined): string | null {
  const text = value?.trim() ?? '';
  return text || null;
}

type TemplateOption = { label: string; value: string };

function withCurrentTemplateOption(
  items: TemplateOption[],
  currentId?: string | null,
): TemplateOption[] {
  const current = currentId?.trim();
  if (!current || items.some((item) => item.value === current)) {
    return items;
  }
  return [{ label: current, value: current }, ...items];
}

export function FissionProductStep({
  productId,
  onDetailChange,
  readOnly = false,
  initialDetail,
  changedKeys = [],
  changedAttrList = [],
}: {
  productId?: number;
  onDetailChange?: (detail: DhProductDetailPublic) => void;
  readOnly?: boolean;
  initialDetail?: DhProductDetailPublic;
  changedKeys?: string[];
  changedAttrList?: DhProductSelectedAttrPublic[];
}) {
  const intl = useIntl();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const supplierId = initialState?.currentUser?.supplier_id;
  const [form] = Form.useForm<ProductFormValues>();
  const changedKeySet = new Set(changedKeys);
  const isChanged = (key: string) => changedKeySet.has(key);
  const changedCategoryAttrIds = changedAttrList
    .map((item) => String(item.attr_id))
    .filter((attrId) => attrId !== DH_CUSTOM_PRODUCT_ATTR_ID);
  const changedCustomValues = changedAttrList.find(
    (item) => String(item.attr_id) === DH_CUSTOM_PRODUCT_ATTR_ID,
  )?.values;
  const onDetailChangeRef = useRef(onDetailChange);
  onDetailChangeRef.current = onDetailChange;

  const [detail, setDetail] = useState<DhProductDetailPublic>();
  const [loading, setLoading] = useState(true);
  const [categoryPath, setCategoryPath] = useState<string>();
  const [cascaderOptions, setCascaderOptions] = useState<CategoryOption[]>([]);
  const [categoryAttrs, setCategoryAttrs] = useState<DhCategoryAttrPublic[]>(
    [],
  );
  const [itemGroupOptions, setItemGroupOptions] = useState<
    ItemGroupCascaderOption[]
  >([]);
  const [itemGroupsReady, setItemGroupsReady] = useState(false);
  const [aftersaleOptions, setAftersaleOptions] = useState<TemplateOption[]>(
    [],
  );
  const [shippingOptions, setShippingOptions] = useState<TemplateOption[]>([]);
  const itemGroupLoadedRef = useRef(false);

  const publishDetail = useCallback((next: DhProductDetailPublic) => {
    setDetail(next);
    onDetailChangeRef.current?.(next);
  }, []);

  const patchDetail = useCallback((patch: Partial<DhProductDetailPublic>) => {
    setDetail((prev) => {
      if (!prev) {
        return prev;
      }
      const next = { ...prev, ...patch };
      onDetailChangeRef.current?.(next);
      return next;
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setDetail(undefined);
    itemGroupLoadedRef.current = false;
    void (async () => {
      try {
        const data =
          initialDetail ??
          (productId ? await fetchDhProductDetail(productId) : undefined);
        if (!data) {
          throw new Error(
            intl.formatMessage({
              id: 'pages.product.detail.loadFailed',
              defaultMessage: '加载商品详情失败',
            }),
          );
        }
        if (cancelled) {
          return;
        }
        let nextCategoryPath: string[] | undefined;
        let nextOptions: CategoryOption[] = [];
        if (data.category?.id) {
          const pathData = await fetchDhCategoryPath(data.category.id);
          if (cancelled) {
            return;
          }
          setCategoryPath(formatCategoryPathDisplay(pathData));
          nextCategoryPath = pathData.path_items.map(
            (item) => item.cate_pub_id,
          );
          nextOptions = await loadCascaderOptionsAlongPath(pathData.path_items);
          const attrs = await fetchDhCategoryAttrs(data.category.id);
          if (!cancelled) {
            setCategoryAttrs(attrs.attrs || []);
          }
        } else {
          setCategoryPath(undefined);
          nextOptions = (await fetchDhCategories({})).map(toCascaderOption);
          setCategoryAttrs([]);
        }
        if (cancelled) {
          return;
        }
        setCascaderOptions(nextOptions);
        publishDetail(data);
        form.setFieldsValue({
          store_id: data.store_id || undefined,
          category_path: nextCategoryPath,
          item_name: data.item_name || '',
          key_word1: data.key_word1 || '',
          key_word2: data.key_word2 || '',
          key_word3: data.key_word3 || '',
          item_group_path: undefined,
          customAttrs: toCustomAttrDrafts(data.attr_list),
        });
      } catch (error) {
        if (!cancelled) {
          setDetail(undefined);
          message.error(
            error instanceof Error
              ? error.message
              : intl.formatMessage({
                  id: 'pages.product.detail.loadFailed',
                  defaultMessage: '加载商品详情失败',
                }),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialDetail, intl, message, productId, publishDetail]);

  useEffect(() => {
    const storeId = detail?.store_id;
    if (!storeId) {
      setAftersaleOptions([]);
      setShippingOptions([]);
      return;
    }
    let cancelled = false;
    void Promise.all([
      fetchStoreAftersaleTemplates(storeId),
      fetchStoreShippingTemplates(storeId),
    ])
      .then(([aftersale, shipping]) => {
        if (cancelled) {
          return;
        }
        setAftersaleOptions(
          aftersale.map((item) => ({
            label: item.name?.trim() || item.after_sale_template_id,
            value: item.after_sale_template_id,
          })),
        );
        setShippingOptions(
          shipping.map((item) => ({
            label: item.name?.trim() || item.shipping_model_id,
            value: item.shipping_model_id,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setAftersaleOptions([]);
          setShippingOptions([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [detail?.store_id]);

  useEffect(() => {
    if (!detail?.store_id) {
      setItemGroupOptions([]);
      setItemGroupsReady(true);
      itemGroupLoadedRef.current = true;
      return;
    }
    const storeId = detail.store_id;
    let cancelled = false;
    itemGroupLoadedRef.current = false;
    setItemGroupsReady(false);
    void (async () => {
      try {
        const data = await fetchStoreProductGroups({
          store_id: storeId,
        });
        if (cancelled) {
          return;
        }
        const options = data.items
          .filter((item) => Boolean(item.group_id))
          .map((item) => toItemGroupCascaderOption(item));
        itemGroupLoadedRef.current = true;
        setItemGroupOptions(options);
        setItemGroupsReady(true);
      } catch {
        if (!cancelled) {
          itemGroupLoadedRef.current = true;
          setItemGroupOptions([]);
          setItemGroupsReady(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [detail?.store_id]);

  const itemGroupPath = useMemo(() => {
    if (!detail?.item_group_id || !itemGroupOptions.length) {
      return undefined;
    }
    return findItemGroupPath(itemGroupOptions, detail.item_group_id);
  }, [detail?.item_group_id, itemGroupOptions]);

  // 分组树就绪后再写入表单路径，并用 options 解析名称（避免 Cascader 回退成 ID）
  useEffect(() => {
    if (!itemGroupsReady) {
      return;
    }
    form.setFieldValue('item_group_path', itemGroupPath);
  }, [form, itemGroupPath, itemGroupsReady]);

  const renderItemGroupDisplay = useCallback(
    (_labels: string[], selectedOptions?: DefaultOptionType[]) => {
      const fromForm = form.getFieldValue('item_group_path') as
        | string[]
        | undefined;
      const fromSelected = selectedOptions
        ?.map((item) => String(item?.value ?? '').trim())
        .filter(Boolean);
      const path =
        (Array.isArray(fromForm) && fromForm.length
          ? fromForm.map(String)
          : undefined) ||
        itemGroupPath ||
        fromSelected;
      return resolveItemGroupLabels(itemGroupOptions, path);
    },
    [form, itemGroupOptions, itemGroupPath],
  );

  const loadCategoryData: CascaderProps<CategoryOption>['loadData'] = (
    selectedOptions,
  ) => {
    const targetOption = selectedOptions[selectedOptions.length - 1];
    if (!targetOption || targetOption.isLeaf || targetOption.children) {
      return;
    }
    targetOption.loading = true;
    setCascaderOptions((prev) => [...prev]);
    void (async () => {
      try {
        const items = await fetchDhCategories({
          parent_id: String(targetOption.value),
        });
        setCascaderOptions((prev) =>
          updateCascaderChildren(
            prev,
            String(targetOption.value),
            items.map(toCascaderOption),
          ),
        );
      } catch (error) {
        targetOption.loading = false;
        setCascaderOptions((prev) => [...prev]);
        message.error(
          error instanceof Error
            ? error.message
            : intl.formatMessage({
                id: 'pages.product.category.loadChildrenFailed',
                defaultMessage: '加载子分类失败',
              }),
        );
      }
    })();
  };

  const onCategoryChange: CascaderProps<CategoryOption>['onChange'] = (
    _value,
    selectedOptions,
  ) => {
    const leaf = selectedOptions?.at(-1) as CategoryOption | undefined;
    if (!leaf) {
      setCategoryPath(undefined);
      setDetail((prev) =>
        prev ? { ...prev, cate_pub_id: '', category: null } : prev,
      );
      setCategoryAttrs([]);
      return;
    }
    void (async () => {
      try {
        const pathData = await fetchDhCategoryPath(leaf.categoryId);
        setCategoryPath(formatCategoryPathDisplay(pathData));
        setCategoryAttrs(
          (await fetchDhCategoryAttrs(leaf.categoryId)).attrs || [],
        );
        setDetail((prev) => {
          if (!prev) {
            return prev;
          }
          const next = { ...prev, cate_pub_id: String(leaf.value) };
          onDetailChangeRef.current?.(next);
          return next;
        });
      } catch (error) {
        message.error(
          error instanceof Error
            ? error.message
            : intl.formatMessage({
                id: 'pages.product.detail.categoryPathFailed',
                defaultMessage: '获取分类全路径失败',
              }),
        );
      }
    })();
  };

  const syncFormValues = (
    values: ProductFormValues,
    changedFields: string[] = [],
  ) => {
    setDetail((prev) => {
      if (!prev) {
        return prev;
      }
      const path = values.item_group_path;
      const nextGroupId = Array.isArray(path)
        ? path.filter(Boolean).at(-1)
        : undefined;
      const next: DhProductDetailPublic = {
        ...prev,
        store_id: values.store_id || prev.store_id,
        ...(values.store_id && values.store_id !== prev.store_id
          ? {
              after_sale_template_id: null,
              shipping_model_id: null,
            }
          : {}),
        item_name:
          values.item_name === undefined
            ? prev.item_name
            : textOrNull(values.item_name),
        key_word1: textOrNull(values.key_word1),
        key_word2: textOrNull(values.key_word2),
        key_word3: textOrNull(values.key_word3),
        item_group_id:
          nextGroupId !== undefined ? String(nextGroupId) : prev.item_group_id,
        attr_list: changedFields.includes('customAttrs')
          ? applyCustomAttrDraftsToAttrList(
              prev.attr_list,
              normalizeCustomAttrDrafts(values.customAttrs),
            )
          : prev.attr_list,
      };
      onDetailChangeRef.current?.(next);
      return next;
    });
  };

  const priceSelectedAttrs = priceProductAttrs(detail?.attr_list);
  const priceAttrIdSet = new Set(
    priceSelectedAttrs.map((item) => String(item.attr_id)),
  );
  const priceCategoryAttrs = priceSelectedAttrs
    .map((item) =>
      categoryAttrs.find(
        (attr) => String(attr.attr_id) === String(item.attr_id),
      ),
    )
    .filter((item): item is DhCategoryAttrPublic => Boolean(item));
  const normalCategoryAttrs = categoryAttrs.filter(
    (attr) => !priceAttrIdSet.has(String(attr.attr_id)),
  );
  const normalSelectedAttrs = nonPriceProductAttrs(detail?.attr_list);

  const handleNormalAttrsChange = useCallback(
    (nextSelected: DhProductSelectedAttrPublic[]) => {
      setDetail((prev) => {
        if (!prev) {
          return prev;
        }
        const managedIds = normalCategoryAttrs.map((item) =>
          String(item.attr_id),
        );
        const updated = {
          ...prev,
          attr_list: mergeManagedAttrsIntoList(
            prev.attr_list,
            managedIds,
            nextSelected,
          ),
        };
        onDetailChangeRef.current?.(updated);
        return updated;
      });
    },
    [normalCategoryAttrs],
  );

  const handlePriceAttrsChange = useCallback(
    (nextSelected: DhProductSelectedAttrPublic[]) => {
      setDetail((prev) => {
        if (!prev) {
          return prev;
        }
        const managedIds = priceCategoryAttrs.map((item) =>
          String(item.attr_id),
        );
        const priced = nextSelected.map((item) => ({
          ...item,
          is_price_attr: '1',
        }));
        const updated = {
          ...prev,
          attr_list: mergeManagedAttrsIntoList(
            prev.attr_list,
            managedIds,
            priced,
          ),
        };
        onDetailChangeRef.current?.(updated);
        return updated;
      });
    },
    [priceCategoryAttrs],
  );

  const handleAttrValuePicChange = useCallback(
    (attrId: string, attrValId: string, picUrl: string | null) => {
      setDetail((prev) => {
        if (!prev) {
          return prev;
        }
        const updated = {
          ...prev,
          attr_list: patchAttrValuePic(
            prev.attr_list,
            attrId,
            attrValId,
            picUrl,
          ),
        };
        onDetailChangeRef.current?.(updated);
        return updated;
      });
    },
    [],
  );

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <ProForm<ProductFormValues>
        key={initialDetail?.id ?? productId}
        form={form}
        disabled={readOnly}
        submitter={false}
        layout="horizontal"
        labelAlign="left"
        labelCol={{ flex: '110px' }}
        wrapperCol={{ flex: 1 }}
        onValuesChange={(changedValues, values) => {
          if (readOnly) {
            return;
          }
          if ('store_id' in changedValues) {
            itemGroupLoadedRef.current = false;
            setItemGroupOptions([]);
          }
          syncFormValues(values, Object.keys(changedValues));
        }}
      >
        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.basic',
            defaultMessage: '基本信息',
          })}
          loading={loading}
        >
          <ProFormSelect
            name="store_id"
            label={changedLabel(
              intl.formatMessage({
                id: 'pages.product.detail.field.storeName',
                defaultMessage: '店铺名称',
              }),
              isChanged('store_id'),
            )}
            showSearch
            debounceTime={300}
            params={{ supplierId }}
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
              style: { maxWidth: 360, ...changedControlStyle(isChanged('store_id')) },
            }}
          />
          <Form.Item
            name="category_path"
            label={changedLabel(
              intl.formatMessage({
                id: 'pages.product.detail.field.productCategory',
                defaultMessage: '产品分类',
              }),
              isChanged('cate_pub_id'),
            )}
          >
            <Cascader
              disabled={readOnly}
              options={cascaderOptions}
              loadData={readOnly ? undefined : loadCategoryData}
              onChange={readOnly ? undefined : onCategoryChange}
              changeOnSelect={false}
              displayRender={(labels) => labels.at(-1) ?? ''}
              placeholder={intl.formatMessage({
                id: 'pages.product.detail.field.categoryPlaceholder',
                defaultMessage: '请选择分类',
              })}
              className={
                isChanged('cate_pub_id') ? 'hm-changed-control' : undefined
              }
              style={{
                maxWidth: 480,
                width: '100%',
                ...changedControlStyle(isChanged('cate_pub_id')),
              }}
            />
          </Form.Item>
          {categoryPath ? (
            <Typography.Text
              style={{
                display: 'block',
                margin: '-8px 0 16px 110px',
                color: isChanged('cate_pub_id') ? CHANGED_COLOR : '#a0522d',
              }}
            >
              {categoryPath}
            </Typography.Text>
          ) : null}
        </Card>

        <Card
          title={changedLabel(
            intl.formatMessage({
              id: 'pages.product.detail.section.attrs',
              defaultMessage: '商品属性',
            }),
            isChanged('attr_list'),
          )}
          loading={loading}
          style={{ marginTop: 16 }}
        >
          <Typography.Text
            strong
            style={{ display: 'block', marginBottom: 12 }}
          >
            {intl.formatMessage({
              id: 'pages.product.detail.categoryAttrs.title',
              defaultMessage: '类目属性',
            })}
          </Typography.Text>
          {normalCategoryAttrs.length > 0 ? (
            <CategoryAttrsFields
              attrs={normalCategoryAttrs}
              selectedAttrs={normalSelectedAttrs}
              disabled={readOnly}
              changedAttrIds={changedCategoryAttrIds}
              onSelectedAttrsChange={
                readOnly ? undefined : handleNormalAttrsChange
              }
            />
          ) : (
            !loading && (
              <Typography.Text type="secondary">
                {intl.formatMessage({
                  id: 'pages.product.detail.categoryAttrs.empty',
                  defaultMessage: '暂无类目属性',
                })}
              </Typography.Text>
            )
          )}
          <Divider />
          <Typography.Text
            strong
            style={{
              display: 'block',
              marginBottom: 12,
              color: changedCustomValues?.length ? CHANGED_COLOR : undefined,
            }}
          >
            {intl.formatMessage({
              id: 'pages.product.detail.customAttrs.title',
              defaultMessage: '自定义属性',
            })}
          </Typography.Text>
          <ProFormList
            name="customAttrs"
            copyIconProps={false}
            deleteIconProps={
              readOnly
                ? false
                : {
                    tooltipText: intl.formatMessage({
                      id: 'pages.product.detail.customAttrs.delete',
                      defaultMessage: '删除',
                    }),
                  }
            }
            creatorButtonProps={
              readOnly
                ? false
                : {
                    creatorButtonText: intl.formatMessage({
                      id: 'pages.product.detail.customAttrs.add',
                      defaultMessage: '新增属性',
                    }),
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
                    marginBottom: 16,
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
                placeholder={intl.formatMessage({
                  id: 'pages.product.detail.attrsCustomNamePlaceholder',
                  defaultMessage: '请输入属性名',
                })}
                fieldProps={{
                  maxLength: DH_CUSTOM_ATTR_MAX_LENGTH,
                  allowClear: true,
                  style: { width: 220 },
                }}
                formItemProps={{ style: { marginBottom: 0 } }}
              />
              <ProFormText
                name="content"
                placeholder={intl.formatMessage({
                  id: 'pages.product.detail.attrsCustomValuePlaceholder',
                  defaultMessage: '请输入属性值',
                })}
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

        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.productInfo',
            defaultMessage: '产品信息',
          })}
          loading={loading}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="item_name"
            label={changedLabel(
              intl.formatMessage({
                id: 'pages.product.detail.field.itemName',
                defaultMessage: '产品标题',
              }),
              isChanged('item_name'),
            )}
            rules={[
              {
                max: ITEM_NAME_MAX_LENGTH,
                message: intl.formatMessage(
                  {
                    id: 'pages.product.detail.field.itemNameMax',
                    defaultMessage: '产品标题最多 {max} 个字符',
                  },
                  { max: ITEM_NAME_MAX_LENGTH },
                ),
              },
            ]}
          >
            <Input
              maxLength={ITEM_NAME_MAX_LENGTH}
              allowClear
              disabled={readOnly}
              style={changedControlStyle(isChanged('item_name'))}
              placeholder={intl.formatMessage({
                id: 'pages.product.detail.field.itemNamePlaceholder',
                defaultMessage: '请输入产品标题',
              })}
            />
          </Form.Item>
          <Form.Item
            label={changedLabel(
              intl.formatMessage({
                id: 'pages.product.detail.field.keywords',
                defaultMessage: '关键词',
              }),
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
                  style={{ width: 240, ...changedControlStyle(isChanged('key_word1')) }}
                />
              </Form.Item>
              <Form.Item name="key_word2" noStyle>
                <Input
                  allowClear
                  disabled={readOnly}
                  style={{ width: 240, ...changedControlStyle(isChanged('key_word2')) }}
                />
              </Form.Item>
              <Form.Item name="key_word3" noStyle>
                <Input
                  allowClear
                  disabled={readOnly}
                  style={{ width: 240, ...changedControlStyle(isChanged('key_word3')) }}
                />
              </Form.Item>
            </Space>
          </Form.Item>
          <Form.Item
            name="item_group_path"
            label={changedLabel(
              intl.formatMessage({
                id: 'pages.product.detail.field.itemGroup',
                defaultMessage: '产品分组',
              }),
              isChanged('item_group_id'),
            )}
          >
            <Cascader
              disabled={readOnly || !itemGroupsReady}
              options={itemGroupOptions}
              changeOnSelect
              allowClear
              displayRender={renderItemGroupDisplay}
              style={{
                maxWidth: 480,
                width: '100%',
                ...changedControlStyle(isChanged('item_group_id')),
              }}
              placeholder={intl.formatMessage({
                id: 'pages.product.detail.field.itemGroupPlaceholder',
                defaultMessage: '请选择产品分组',
              })}
            />
          </Form.Item>
          <Form.Item
            label={intl.formatMessage({
              id: 'pages.product.detail.field.productState',
              defaultMessage: '商品状态',
            })}
          >
            {formatProductState(detail?.state, (id, defaultMessage) =>
              intl.formatMessage({ id, defaultMessage }),
            )}
          </Form.Item>
          <Form.Item
            label={intl.formatMessage({
              id: 'pages.product.detail.field.syncState',
              defaultMessage: '同步状态',
            })}
          >
            {formatSyncState(
              detail?.sync_state,
              intl.formatMessage({
                id: 'pages.product.detail.sync.success',
                defaultMessage: '成功',
              }),
              intl.formatMessage({
                id: 'pages.product.detail.sync.fail',
                defaultMessage: '失败',
              }),
            )}
          </Form.Item>
          <Form.Item
            label={intl.formatMessage({
              id: 'pages.product.list.field.lastSyncedAt',
              defaultMessage: '同步时间',
            })}
          >
            {formatDateTime(detail?.last_synced_at)}
          </Form.Item>
        </Card>
      </ProForm>

      <Card
        title={changedLabel(
          intl.formatMessage({
            id: 'pages.product.detail.section.images',
            defaultMessage: '商品图片',
          }),
          isChanged('item_img_list'),
        )}
        loading={loading}
      >
        {loading ? null : (
          <ProductImagesEditor
            images={detail?.item_img_list}
            disabled={readOnly}
            storeId={detail?.store_id || undefined}
            alt={detail?.item_name || detail?.item_code}
            onChange={(next) => {
              setDetail((prev) => {
                if (!prev) {
                  return prev;
                }
                const updated = { ...prev, item_img_list: next };
                onDetailChangeRef.current?.(updated);
                return updated;
              });
            }}
          />
        )}
      </Card>

      <Card
        title={changedLabel(
          intl.formatMessage({
            id: 'pages.product.detail.section.specAttrs',
            defaultMessage: '商品规格',
          }),
          isChanged('sku_list') ||
            isChanged('item_spec_self_def_list') ||
            changedCategoryAttrIds.some((id) => priceAttrIdSet.has(id)),
        )}
        loading={loading}
      >
        <SpecAttrsFields
          disabled={readOnly}
          changedAttrIds={changedCategoryAttrIds}
          priceCategoryAttrs={priceCategoryAttrs}
          priceSelectedAttrs={priceSelectedAttrs}
          specSelfDefs={detail?.item_spec_self_def_list}
          storeId={detail?.store_id || undefined}
          onSelectedAttrsChange={
            readOnly ? undefined : handlePriceAttrsChange
          }
          onValuePicChange={
            readOnly ? undefined : handleAttrValuePicChange
          }
          onSpecSelfDefsChange={(next) => {
            setDetail((prev) => {
              if (!prev) {
                return prev;
              }
              const updated = { ...prev, item_spec_self_def_list: next };
              onDetailChangeRef.current?.(updated);
              return updated;
            });
          }}
        />
        <Divider plain>
          {intl.formatMessage({
            id: 'pages.product.detail.specSku.divider',
            defaultMessage: '商品规格属性生成的规格sku',
          })}
        </Divider>
        <SpecSkuTable
          disabled={readOnly}
          skuList={detail?.sku_list}
          priceSelectedAttrs={priceSelectedAttrs}
          specSelfDefs={detail?.item_spec_self_def_list}
          itemCode={detail?.item_code}
          onChange={(next) => {
            setDetail((prev) => {
              if (!prev) {
                return prev;
              }
              const updated = { ...prev, sku_list: next };
              onDetailChangeRef.current?.(updated);
              return updated;
            });
          }}
        />
      </Card>

      {detail?.html_content ? (
        <Card
          title={changedLabel(
            intl.formatMessage({
              id: 'pages.product.detail.section.html',
              defaultMessage: '详情描述',
            }),
            isChanged('html_content'),
          )}
        >
          <iframe
            title={intl.formatMessage({
              id: 'pages.product.detail.section.html',
              defaultMessage: '详情描述',
            })}
            srcDoc={detail.html_content}
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
        title={intl.formatMessage({
          id: 'pages.product.detail.section.templates',
          defaultMessage: '模板信息',
        })}
        loading={loading}
      >
        <div style={{ maxWidth: 720 }}>
          <div style={{ display: 'flex', marginBottom: 24 }}>
            <div
              style={{
                width: 110,
                flex: '0 0 110px',
                lineHeight: '32px',
                ...changedControlStyle(isChanged('after_sale_template_id')),
              }}
            >
              {intl.formatMessage({
                id: 'pages.product.detail.field.afterSaleTemplate',
                defaultMessage: '售后模板',
              })}
            </div>
            <Select
              disabled={readOnly}
              allowClear
              showSearch
              optionFilterProp="label"
              style={{
                maxWidth: 360,
                width: '100%',
                ...changedControlStyle(isChanged('after_sale_template_id')),
              }}
              placeholder={intl.formatMessage({
                id: 'pages.product.detail.field.afterSaleTemplatePlaceholder',
                defaultMessage: '请选择售后模板',
              })}
              options={withCurrentTemplateOption(
                aftersaleOptions,
                detail?.after_sale_template_id,
              )}
              value={detail?.after_sale_template_id || undefined}
              onChange={(value) => {
                patchDetail({ after_sale_template_id: value || null });
              }}
            />
          </div>
          <div style={{ display: 'flex' }}>
            <div
              style={{
                width: 110,
                flex: '0 0 110px',
                lineHeight: '32px',
                ...changedControlStyle(isChanged('shipping_model_id')),
              }}
            >
              {intl.formatMessage({
                id: 'pages.product.detail.field.shippingTemplate',
                defaultMessage: '物流模板',
              })}
            </div>
            <Select
              disabled={readOnly}
              allowClear
              showSearch
              optionFilterProp="label"
              style={{
                maxWidth: 360,
                width: '100%',
                ...changedControlStyle(isChanged('shipping_model_id')),
              }}
              placeholder={intl.formatMessage({
                id: 'pages.product.detail.field.shippingTemplatePlaceholder',
                defaultMessage: '请选择物流模板',
              })}
              options={withCurrentTemplateOption(
                shippingOptions,
                detail?.shipping_model_id,
              )}
              value={detail?.shipping_model_id || undefined}
              onChange={(value) => {
                patchDetail({ shipping_model_id: value || null });
              }}
            />
          </div>
        </div>
      </Card>
    </Space>
  );
}
