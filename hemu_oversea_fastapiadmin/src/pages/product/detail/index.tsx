import type { ProFormInstance } from '@ant-design/pro-components';
import {
  PageContainer,
  ProForm,
  ProFormList,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { history, useIntl, useLocation, useModel } from '@umijs/max';
import {
  App,
  Button,
  Card,
  Cascader,
  Divider,
  Form,
  Input,
  Space,
  Typography,
} from 'antd';
import type { CascaderProps, DefaultOptionType } from 'antd/es/cascader';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  fetchDhCategories,
  fetchDhCategoryAttrs,
  fetchDhCategoryPath,
} from '@/services/admin/categories';
import {
  fetchDhProductDetail,
  fetchDhProductGroup,
  fetchDhProductGroupList,
} from '@/services/admin/products';
import { fetchStoreList } from '@/services/admin/stores';
import type {
  DhCategoryAttrPublic,
  DhCategoryPathPublic,
  DhCategoryPublic,
  DhProductDetailPublic,
  DhProductGroupPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';
import {
  DH_PRODUCT_STATE_LABEL,
  DH_PRODUCT_STATES,
  type DhProductStateCode,
} from '@/constants/product';
import { formatDateTime } from '@/utils/datetime';
import {
  PRODUCT_LIST_PATH,
  createEmptyProductDetail,
  isProductPageEditable,
  productCreatePath,
  productEditPath,
  resolveProductPageRoute,
  toCopyProductDetail,
  type ProductPageMode,
} from '../utils';
import CategoryAttrsFields from './CategoryAttrsFields';
import ProductImagesEditor from './ProductImagesEditor';
import SpecAttrsFields from './SpecAttrsFields';
import SpecSkuTable from './SpecSkuTable';

/** 与敦煌 itemName / 裂变 update_info.item_name 上限一致 */
const ITEM_NAME_MAX_LENGTH = 140;

type BasicFormValues = {
  store_id?: number;
  category_path?: string[];
};

type ProductInfoFormValues = {
  item_name?: string;
  key_word1?: string;
  key_word2?: string;
  key_word3?: string;
  item_group_path?: string[];
};

type ItemGroupCascaderOption = DefaultOptionType & {
  value: string;
  label: string;
  isLeaf?: boolean;
  children?: ItemGroupCascaderOption[];
};

type CategoryOption = DefaultOptionType & {
  value: string;
  label: string;
  categoryId: number;
  isLeaf?: boolean;
  loading?: boolean;
  children?: CategoryOption[];
};

/** 官方：自定义产品属性 attrId 默认为 11 */
const DH_CUSTOM_PRODUCT_ATTR_ID = '11';
/** 发布接口：自定义属性最多 20 个，名称/值不超过 40 字符 */
const DH_CUSTOM_ATTR_MAX_COUNT = 20;
const DH_CUSTOM_ATTR_MAX_LENGTH = 40;

function isCustomProductAttr(attr: DhProductSelectedAttrPublic) {
  return String(attr.attr_id) === DH_CUSTOM_PRODUCT_ATTR_ID;
}

function isPriceProductAttr(attr: DhProductSelectedAttrPublic) {
  return String(attr.is_price_attr) === '1';
}

function categoryProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return (list || []).filter((item) => !isCustomProductAttr(item));
}

/** 影响 SKU 的价格规格属性（is_price_attr=1） */
function priceProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return categoryProductAttrs(list).filter(isPriceProductAttr);
}

/** 普通产品属性（非价格规格、非自定义 attrId=11） */
function nonPriceProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return categoryProductAttrs(list).filter((item) => !isPriceProductAttr(item));
}

/** 写入 / 覆盖指定属性值的 pic_url；若属性值不存在则追加 */
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

function customProductAttrValues(list?: DhProductSelectedAttrPublic[]) {
  return (list || [])
    .filter(isCustomProductAttr)
    .flatMap((item) => item.values || []);
}

type CustomAttrDraft = {
  key: string;
  attr_val_id: string | null;
  attr_name: string;
  content: string;
};

function toCustomAttrDrafts(
  list?: DhProductSelectedAttrPublic[],
): CustomAttrDraft[] {
  return customProductAttrValues(list).map((item, index) => ({
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

/** 将自定义属性草稿写回 attr_list（attr_id=11，发布时可不传 attrValId） */
function applyCustomAttrDraftsToAttrList(
  list: DhProductSelectedAttrPublic[] | undefined,
  drafts: CustomAttrDraft[],
): DhProductSelectedAttrPublic[] {
  const others = (list || []).filter((item) => !isCustomProductAttr(item));
  const values = drafts
    .map((item, index) => ({
      attr_id: DH_CUSTOM_PRODUCT_ATTR_ID,
      attr_val_id: item.attr_val_id || String(index + 1),
      attr_name: item.attr_name.trim() || null,
      attr_name_cn: null,
      line_attrval_name: item.content.trim() || null,
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

function groupDisplayName(group: DhProductGroupPublic): string {
  return (group.group_name || group.group_en_name || group.group_id).trim();
}

function toItemGroupCascaderOption(
  group: DhProductGroupPublic,
): ItemGroupCascaderOption {
  const children = (group.children || [])
    .filter((item) => Boolean(item.group_id))
    .map((item) => toItemGroupCascaderOption(item));
  return {
    value: group.group_id,
    label: groupDisplayName(group),
    isLeaf: children.length === 0,
    children: children.length ? children : undefined,
  };
}

function toItemGroupCascaderOptions(
  groups: DhProductGroupPublic[],
): ItemGroupCascaderOption[] {
  return groups
    .filter((item) => Boolean(item.group_id))
    .map((item) => toItemGroupCascaderOption(item));
}

function findItemGroupPath(
  options: ItemGroupCascaderOption[],
  targetId: string,
  path: string[] = [],
): string[] | undefined {
  for (const option of options) {
    const next = [...path, option.value];
    if (option.value === targetId) {
      return next;
    }
    if (option.children?.length) {
      const found = findItemGroupPath(option.children, targetId, next);
      if (found) {
        return found;
      }
    }
  }
  return undefined;
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

function pageTitleId(mode: ProductPageMode): {
  id: string;
  defaultMessage: string;
} {
  switch (mode) {
    case 'create':
      return {
        id: 'pages.product.create.title',
        defaultMessage: '新建商品',
      };
    case 'copy':
      return {
        id: 'pages.product.copy.title',
        defaultMessage: '复制商品',
      };
    case 'edit':
      return {
        id: 'pages.product.edit.title',
        defaultMessage: '编辑商品',
      };
    default:
      return {
        id: 'pages.product.detail.title',
        defaultMessage: '商品详情',
      };
  }
}

const ProductDetailPage: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const location = useLocation();
  const { initialState } = useModel('@@initialState');
  const supplierId = initialState?.currentUser?.supplier_id;
  const routeState = useMemo(
    () => resolveProductPageRoute(location.pathname, location.search),
    [location.pathname, location.search],
  );
  const { mode, productId, fromId } = routeState;
  const editable = isProductPageEditable(mode);
  const sourceProductId = mode === 'copy' ? fromId : productId;
  const formRef = useRef<ProFormInstance<BasicFormValues>>(null);

  const [detail, setDetail] = useState<DhProductDetailPublic>();
  const [loading, setLoading] = useState(true);
  const [categoryPath, setCategoryPath] = useState<string>();
  const [cascaderOptions, setCascaderOptions] = useState<CategoryOption[]>([]);
  const [initialCategoryPath, setInitialCategoryPath] = useState<string[]>();
  const [categoryAttrs, setCategoryAttrs] = useState<DhCategoryAttrPublic[]>([]);
  const [attrFillValues, setAttrFillValues] = useState<
    DhProductSelectedAttrPublic[] | undefined
  >();
  const [customAttrDrafts, setCustomAttrDrafts] = useState<CustomAttrDraft[]>(
    [],
  );
  const [attrsLoading, setAttrsLoading] = useState(false);
  const attrsReqRef = useRef(0);
  const originalCategoryIdRef = useRef<number>();
  const productInfoFormRef = useRef<ProFormInstance<ProductInfoFormValues>>(null);
  const [itemGroupOptions, setItemGroupOptions] = useState<
    ItemGroupCascaderOption[]
  >([]);
  const itemGroupReqRef = useRef(0);
  const itemGroupTreeLoadedRef = useRef(false);
  const [selectedStoreId, setSelectedStoreId] = useState<number>();

  const applyCategoryPath = useCallback(async (categoryLocalId: number) => {
    const pathData = await fetchDhCategoryPath(categoryLocalId);
    setCategoryPath(formatCategoryPathDisplay(pathData));
    return pathData;
  }, []);

  const loadItemGroups = useCallback(async () => {
    if (!detail?.store_id || itemGroupTreeLoadedRef.current) {
      return;
    }
    const reqId = itemGroupReqRef.current + 1;
    itemGroupReqRef.current = reqId;
    try {
      const data = await fetchDhProductGroupList({
        store_id: detail.store_id,
        page: 1,
        page_size: 100,
      });
      if (itemGroupReqRef.current !== reqId) {
        return;
      }
      const options = toItemGroupCascaderOptions(data.items);
      itemGroupTreeLoadedRef.current = true;
      setItemGroupOptions(options);
      const currentId =
        productInfoFormRef.current
          ?.getFieldValue('item_group_path')
          ?.at(-1) || detail.item_group_id;
      if (currentId) {
        const path = findItemGroupPath(options, currentId);
        if (path) {
          productInfoFormRef.current?.setFieldValue('item_group_path', path);
        }
      }
    } catch (error) {
      if (itemGroupReqRef.current !== reqId) {
        return;
      }
      message.error(
        error instanceof Error
          ? error.message
          : intl.formatMessage({
              id: 'pages.product.detail.itemGroupLoadFailed',
              defaultMessage: '加载产品分组失败',
            }),
      );
    }
  }, [detail?.item_group_id, detail?.store_id, intl, message]);

  const loadCategoryAttrs = useCallback(
    async (
      categoryLocalId: number | null | undefined,
      selectedAttrs?: DhProductSelectedAttrPublic[],
    ) => {
      const reqId = attrsReqRef.current + 1;
      attrsReqRef.current = reqId;
      if (!categoryLocalId) {
        setCategoryAttrs([]);
        setAttrFillValues(undefined);
        setAttrsLoading(false);
        return;
      }
      setAttrsLoading(true);
      try {
        const data = await fetchDhCategoryAttrs(categoryLocalId);
        if (attrsReqRef.current !== reqId) {
          return;
        }
        setCategoryAttrs(data.attrs || []);
        setAttrFillValues(selectedAttrs);
      } catch (error) {
        if (attrsReqRef.current !== reqId) {
          return;
        }
        setCategoryAttrs([]);
        setAttrFillValues(undefined);
        message.error(
          error instanceof Error
            ? error.message
            : intl.formatMessage({
                id: 'pages.product.detail.attrsLoadFailed',
                defaultMessage: '加载分类属性失败',
              }),
        );
      } finally {
        if (attrsReqRef.current === reqId) {
          setAttrsLoading(false);
        }
      }
    },
    [intl, message],
  );

  const loadDetail = useCallback(async () => {
    const resetEmpty = () => {
      setDetail(undefined);
      setSelectedStoreId(undefined);
      setCategoryPath(undefined);
      setCascaderOptions([]);
      setInitialCategoryPath(undefined);
      setCategoryAttrs([]);
      setAttrFillValues(undefined);
      setCustomAttrDrafts([]);
      originalCategoryIdRef.current = undefined;
    };

    if (mode === 'create') {
      setLoading(true);
      try {
        const roots = (await fetchDhCategories({})).map(toCascaderOption);
        setCascaderOptions(roots);
        setInitialCategoryPath(undefined);
        setCategoryPath(undefined);
        setCategoryAttrs([]);
        setAttrFillValues(undefined);
        setCustomAttrDrafts([]);
        originalCategoryIdRef.current = undefined;
        setSelectedStoreId(undefined);
        setDetail(createEmptyProductDetail());
      } catch (error) {
        resetEmpty();
        message.error(
          error instanceof Error
            ? error.message
            : intl.formatMessage({
                id: 'pages.product.category.loadFailed',
                defaultMessage: '加载商品分类失败',
              }),
        );
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!sourceProductId) {
      resetEmpty();
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const data = await fetchDhProductDetail(sourceProductId);
      const nextDetail =
        mode === 'copy' ? toCopyProductDetail(data) : data;
      let nextCategoryPath: string[] | undefined;
      let nextOptions: CategoryOption[] = [];

      if (nextDetail.category?.id) {
        try {
          const pathData = await applyCategoryPath(nextDetail.category.id);
          nextCategoryPath = pathData.path_items.map((item) => item.cate_pub_id);
          nextOptions = await loadCascaderOptionsAlongPath(pathData.path_items);
        } catch (pathError) {
          setCategoryPath(formatCategoryLabel(nextDetail.category));
          nextOptions = (await fetchDhCategories({})).map(toCascaderOption);
          const fallbackId =
            nextDetail.cate_pub_id || nextDetail.category.cate_pub_id;
          nextCategoryPath = fallbackId ? [fallbackId] : undefined;
          message.error(
            pathError instanceof Error
              ? pathError.message
              : intl.formatMessage({
                  id: 'pages.product.detail.categoryPathFailed',
                  defaultMessage: '获取分类全路径失败',
                }),
          );
        }
      } else {
        setCategoryPath(undefined);
        nextOptions = (await fetchDhCategories({})).map(toCascaderOption);
      }

      setCascaderOptions(nextOptions);
      setInitialCategoryPath(nextCategoryPath);
      setSelectedStoreId(nextDetail.store_id || undefined);
      setDetail(nextDetail);
      setCustomAttrDrafts(toCustomAttrDrafts(nextDetail.attr_list));
      originalCategoryIdRef.current = nextDetail.category?.id;
      await loadCategoryAttrs(
        nextDetail.category?.id,
        categoryProductAttrs(nextDetail.attr_list),
      );
    } catch (error) {
      resetEmpty();
      message.error(
        error instanceof Error
          ? error.message
          : intl.formatMessage({
              id: 'pages.product.detail.loadFailed',
              defaultMessage: '加载商品详情失败',
            }),
      );
    } finally {
      setLoading(false);
    }
  }, [
    applyCategoryPath,
    intl,
    loadCategoryAttrs,
    message,
    mode,
    sourceProductId,
  ]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    itemGroupTreeLoadedRef.current = false;
    if (!detail?.store_id || !detail.item_group_id) {
      setItemGroupOptions([]);
      return;
    }
    const storeId = detail.store_id;
    const groupId = detail.item_group_id;
    let cancelled = false;
    void fetchDhProductGroup(
      {
        store_id: storeId,
        group_id: groupId,
      },
      { skipErrorHandler: true },
    )
      .then((group) => {
        if (cancelled || itemGroupTreeLoadedRef.current) {
          return;
        }
        setItemGroupOptions([toItemGroupCascaderOption(group)]);
      })
      .catch(() => {
        if (cancelled || itemGroupTreeLoadedRef.current) {
          return;
        }
        setItemGroupOptions([
          {
            value: groupId,
            label: groupId,
            isLeaf: true,
          },
        ]);
      });
    return () => {
      cancelled = true;
    };
  }, [detail?.item_group_id, detail?.store_id]);

  const syncCustomAttrDrafts = (next: CustomAttrDraft[]) => {
    const normalized = next.map((item, index) => ({
      key: item.key || `custom-${index}-${Date.now()}`,
      attr_val_id: item.attr_val_id ?? null,
      attr_name: item.attr_name ?? '',
      content: item.content ?? '',
    }));
    setCustomAttrDrafts(normalized);
    setDetail((prev) =>
      prev
        ? {
            ...prev,
            attr_list: applyCustomAttrDraftsToAttrList(
              prev.attr_list,
              normalized,
            ),
          }
        : prev,
    );
    setAttrFillValues((prev) =>
      prev ? applyCustomAttrDraftsToAttrList(prev, normalized) : prev,
    );
  };

  const loadCascaderData: CascaderProps<CategoryOption>['loadData'] = (
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
    value,
    selectedOptions,
  ) => {
    if (!value?.length || !selectedOptions?.length) {
      setCategoryPath(undefined);
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              cate_pub_id: '',
              category: null,
            }
          : prev,
      );
      void loadCategoryAttrs(null);
      return;
    }

    const leaf = selectedOptions[selectedOptions.length - 1] as
      | CategoryOption
      | undefined;
    if (!leaf?.isLeaf || !leaf.categoryId) {
      return;
    }

    void (async () => {
      try {
        const pathData = await applyCategoryPath(leaf.categoryId);
        const selectedCategory =
          pathData.path_items[pathData.path_items.length - 1] ?? null;
        setDetail((prev) =>
          prev
            ? {
                ...prev,
                cate_pub_id: String(leaf.value),
                category: selectedCategory,
              }
            : prev,
        );
        const sameAsProduct =
          leaf.categoryId === originalCategoryIdRef.current;
        void loadCategoryAttrs(
          leaf.categoryId,
          sameAsProduct
            ? categoryProductAttrs(detail?.attr_list)
            : undefined,
        );
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

  const routeInvalid =
    (mode === 'view' || mode === 'edit') && !productId
      ? true
      : mode === 'copy' && !fromId;

  if (routeInvalid) {
    return (
      <PageContainer
        title={false}
        onBack={() => history.push(PRODUCT_LIST_PATH)}
      >
        <Card>
          {intl.formatMessage({
            id: 'pages.product.detail.invalidId',
            defaultMessage: '商品 ID 无效',
          })}
        </Card>
      </PageContainer>
    );
  }

  const formInstanceKey =
    mode === 'create'
      ? 'create'
      : mode === 'copy'
        ? `copy-${fromId}`
        : `${mode}-${productId}`;

  const priceSelectedAttrs = priceProductAttrs(
    attrFillValues || detail?.attr_list,
  );
  const priceAttrIdSet = new Set(
    priceSelectedAttrs.map((item) => String(item.attr_id)),
  );
  const priceCategoryAttrs = priceSelectedAttrs
    .map((item) =>
      categoryAttrs.find((attr) => String(attr.attr_id) === String(item.attr_id)),
    )
    .filter((item): item is DhCategoryAttrPublic => Boolean(item));
  const normalCategoryAttrs = categoryAttrs.filter(
    (attr) => !priceAttrIdSet.has(String(attr.attr_id)),
  );
  const normalSelectedAttrs = nonPriceProductAttrs(
    attrFillValues || detail?.attr_list,
  );
  const titleMsg = pageTitleId(mode);

  return (
    <PageContainer
      title={intl.formatMessage(titleMsg)}
      onBack={() => history.push(PRODUCT_LIST_PATH)}
      extra={
        mode === 'view' && productId ? (
          <Space wrap>
            <Button
              type="primary"
              onClick={() => history.push(productEditPath(productId))}
            >
              {intl.formatMessage({
                id: 'pages.product.action.edit',
                defaultMessage: '编辑',
              })}
            </Button>
            <Button
              onClick={() =>
                history.push(productCreatePath({ from: productId }))
              }
            >
              {intl.formatMessage({
                id: 'pages.product.action.copy',
                defaultMessage: '复制',
              })}
            </Button>
          </Space>
        ) : undefined
      }
    >
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.basic',
            defaultMessage: '基本信息',
          })}
          loading={loading}
        >
          {detail ? (
            <ProForm<BasicFormValues>
              key={`basic-${formInstanceKey}`}
              formRef={formRef}
              submitter={false}
              disabled={!editable}
              layout="horizontal"
              labelAlign="left"
              labelCol={{ flex: '110px' }}
              wrapperCol={{ flex: 1 }}
              style={{ maxWidth: 720 }}
              initialValues={{
                store_id: detail.store_id || undefined,
                category_path: initialCategoryPath,
              }}
              onValuesChange={(changed) => {
                if ('store_id' in changed) {
                  const nextStoreId = changed.store_id as number | undefined;
                  setSelectedStoreId(nextStoreId);
                  itemGroupTreeLoadedRef.current = false;
                  setItemGroupOptions([]);
                  setDetail((prev) =>
                    prev
                      ? {
                          ...prev,
                          store_id: nextStoreId || 0,
                        }
                      : prev,
                  );
                }
              }}
            >
              <ProFormSelect
                name="store_id"
                label={intl.formatMessage({
                  id: 'pages.product.detail.field.storeName',
                  defaultMessage: '店铺名称',
                })}
                rules={[
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'pages.product.detail.field.storeNameRequired',
                      defaultMessage: '请选择店铺',
                    }),
                  },
                ]}
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
                  placeholder: intl.formatMessage({
                    id: 'pages.product.list.field.storePlaceholder',
                    defaultMessage: '请选择店铺',
                  }),
                  style: { maxWidth: 360 },
                }}
              />
              <div style={{ marginBottom: categoryPath ? 0 : undefined }}>
                <Form.Item
                  name="category_path"
                  label={intl.formatMessage({
                    id: 'pages.product.detail.field.productCategory',
                    defaultMessage: '产品分类',
                  })}
                  required
                  rules={[
                    {
                      required: true,
                      type: 'array',
                      min: 1,
                      message: intl.formatMessage({
                        id: 'pages.product.detail.categoryRequired',
                        defaultMessage: '请选择分类',
                      }),
                    },
                  ]}
                  style={{ marginBottom: categoryPath ? 8 : undefined }}
                >
                  <Cascader
                    options={cascaderOptions}
                    loadData={loadCascaderData}
                    onChange={onCategoryChange}
                    changeOnSelect={false}
                    displayRender={(labels) => labels.at(-1) ?? ''}
                    placeholder={intl.formatMessage({
                      id: 'pages.product.detail.field.categoryPlaceholder',
                      defaultMessage: '请选择分类',
                    })}
                    style={{ maxWidth: 480, width: '100%' }}
                    optionRender={(option) => (
                      <span
                        title={String(option.label ?? '')}
                        style={{
                          display: 'inline-block',
                          maxWidth: 150,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          verticalAlign: 'bottom',
                        }}
                      >
                        {option.label}
                      </span>
                    )}
                  />
                </Form.Item>
                {categoryPath ? (
                  <Typography.Text
                    style={{
                      display: 'block',
                      marginBottom: 24,
                      color: '#a0522d',
                      lineHeight: 1.5,
                      wordBreak: 'break-word',
                    }}
                  >
                    {categoryPath}
                  </Typography.Text>
                ) : null}
              </div>
            </ProForm>
          ) : (
            !loading &&
            intl.formatMessage({
              id: 'pages.product.detail.notFound',
              defaultMessage: '未找到该商品',
            })
          )}
        </Card>

        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.attrs',
            defaultMessage: '商品属性',
          })}
          loading={loading || attrsLoading}
        >
          <div style={{ marginBottom: 20 }}>
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
                disabled={!editable}
              />
            ) : (
              !loading &&
              !attrsLoading && (
                <Typography.Text type="secondary">
                  {intl.formatMessage({
                    id: 'pages.product.detail.categoryAttrs.empty',
                    defaultMessage: '暂无类目属性',
                  })}
                </Typography.Text>
              )
            )}
          </div>

          <Divider style={{ margin: '8px 0 16px' }} />

          <div>
            <Typography.Text
              strong
              style={{ display: 'block', marginBottom: 12 }}
            >
              {intl.formatMessage({
                id: 'pages.product.detail.customAttrs.title',
                defaultMessage: '自定义属性',
              })}
            </Typography.Text>
            <ProForm<{ customAttrs: CustomAttrDraft[] }>
              key={`custom-attrs-${formInstanceKey}`}
              submitter={false}
              disabled={!editable}
              initialValues={{ customAttrs: customAttrDrafts }}
              onValuesChange={(_, values) => {
                if (!editable) {
                  return;
                }
                syncCustomAttrDrafts(values.customAttrs || []);
              }}
            >
              <ProFormList
                name="customAttrs"
                copyIconProps={false}
                deleteIconProps={
                  editable
                    ? {
                        tooltipText: intl.formatMessage({
                          id: 'pages.product.detail.customAttrs.delete',
                          defaultMessage: '删除',
                        }),
                      }
                    : false
                }
                creatorButtonProps={
                  editable
                    ? {
                        creatorButtonText: intl.formatMessage({
                          id: 'pages.product.detail.customAttrs.add',
                          defaultMessage: '新增属性',
                        }),
                        type: 'dashed',
                        style: { width: '100%', maxWidth: 720 },
                      }
                    : false
                }
                max={DH_CUSTOM_ATTR_MAX_COUNT}
                creatorRecord={() => ({
                  key: `custom-new-${Date.now()}`,
                  attr_val_id: null,
                  attr_name: '',
                  content: '',
                })}
                itemRender={({ listDom, action }) => (
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 16,
                    }}
                  >
                    {listDom}
                    {editable ? action : null}
                  </div>
                )}
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
                    formItemProps={{
                      style: { marginBottom: 0 },
                    }}
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
                    formItemProps={{
                      style: { marginBottom: 0 },
                    }}
                  />
                </Space>
              </ProFormList>
            </ProForm>
          </div>
        </Card>

        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.productInfo',
            defaultMessage: '产品信息',
          })}
          loading={loading}
        >
          {detail ? (
            <ProForm<ProductInfoFormValues>
              key={`product-info-${formInstanceKey}`}
              formRef={productInfoFormRef}
              submitter={false}
              disabled={!editable}
              layout="horizontal"
              labelAlign="left"
              labelCol={{ flex: '110px' }}
              wrapperCol={{ flex: 1 }}
              style={{ maxWidth: 920 }}
              initialValues={{
                item_name: detail.item_name || '',
                key_word1: detail.key_word1 || '',
                key_word2: detail.key_word2 || '',
                key_word3: detail.key_word3 || '',
                item_group_path: detail.item_group_id
                  ? [detail.item_group_id]
                  : undefined,
              }}
            >
              <Form.Item
                name="item_name"
                label={intl.formatMessage({
                  id: 'pages.product.detail.field.itemName',
                  defaultMessage: '产品标题',
                })}
                required
                rules={[
                  {
                    required: true,
                    whitespace: true,
                    message: intl.formatMessage({
                      id: 'pages.product.detail.field.itemNameRequired',
                      defaultMessage: '请输入产品标题',
                    }),
                  },
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
                extra={
                  <Form.Item
                    noStyle
                    shouldUpdate={(prev, next) =>
                      prev.item_name !== next.item_name
                    }
                  >
                    {({ getFieldValue }) => {
                      const used = String(
                        getFieldValue('item_name') || '',
                      ).length;
                      const remaining = Math.max(
                        0,
                        ITEM_NAME_MAX_LENGTH - used,
                      );
                      return (
                        <Typography.Text type="secondary">
                          {intl.formatMessage(
                            {
                              id: 'pages.product.detail.field.itemNameRemaining',
                              defaultMessage: '您还可以输入{count}个字符',
                            },
                            { count: remaining },
                          )}
                        </Typography.Text>
                      );
                    }}
                  </Form.Item>
                }
              >
                <Input
                  maxLength={ITEM_NAME_MAX_LENGTH}
                  allowClear
                  style={{ width: '100%' }}
                  placeholder={intl.formatMessage({
                    id: 'pages.product.detail.field.itemNamePlaceholder',
                    defaultMessage: '请输入产品标题',
                  })}
                />
              </Form.Item>
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.product.detail.field.keywords',
                  defaultMessage: '关键词',
                })}
              >
                <Space size={12} wrap style={{ width: '100%' }}>
                  <Form.Item name="key_word1" noStyle>
                    <Input
                      allowClear
                      style={{ width: 240 }}
                      placeholder={intl.formatMessage({
                        id: 'pages.product.detail.field.keywordPlaceholder',
                        defaultMessage: '关键词 1',
                      })}
                    />
                  </Form.Item>
                  <Form.Item name="key_word2" noStyle>
                    <Input
                      allowClear
                      style={{ width: 240 }}
                      placeholder={intl.formatMessage({
                        id: 'pages.product.detail.field.keywordPlaceholder2',
                        defaultMessage: '关键词 2',
                      })}
                    />
                  </Form.Item>
                  <Form.Item name="key_word3" noStyle>
                    <Input
                      allowClear
                      style={{ width: 240 }}
                      placeholder={intl.formatMessage({
                        id: 'pages.product.detail.field.keywordPlaceholder3',
                        defaultMessage: '关键词 3',
                      })}
                    />
                  </Form.Item>
                </Space>
              </Form.Item>
              <Form.Item
                name="item_group_path"
                label={intl.formatMessage({
                  id: 'pages.product.detail.field.itemGroup',
                  defaultMessage: '产品分组',
                })}
              >
                <Cascader
                  options={itemGroupOptions}
                  changeOnSelect
                  allowClear
                  displayRender={(labels) => labels.join(' / ')}
                  placeholder={intl.formatMessage({
                    id: 'pages.product.detail.field.itemGroupPlaceholder',
                    defaultMessage: '请选择产品分组',
                  })}
                  style={{ maxWidth: 480, width: '100%' }}
                  popupMenuColumnStyle={{
                    width: 220,
                    maxWidth: 220,
                  }}
                  showSearch={{
                    filter: (inputValue, path) =>
                      path.some((option) =>
                        String(option.label ?? '')
                          .toLowerCase()
                          .includes(inputValue.trim().toLowerCase()),
                      ),
                  }}
                  onOpenChange={(open) => {
                    if (open) {
                      void loadItemGroups();
                    }
                  }}
                />
              </Form.Item>
              {mode === 'view' || mode === 'edit' ? (
                <>
                  <Form.Item
                    label={intl.formatMessage({
                      id: 'pages.product.detail.field.productState',
                      defaultMessage: '商品状态',
                    })}
                  >
                    {formatProductState(
                      detail.state,
                      (id, defaultMessage) =>
                        intl.formatMessage({ id, defaultMessage }),
                    )}
                  </Form.Item>
                  <Form.Item
                    label={intl.formatMessage({
                      id: 'pages.product.list.field.lastSyncedAt',
                      defaultMessage: '同步时间',
                    })}
                    style={{ marginBottom: 0 }}
                  >
                    {formatDateTime(detail.last_synced_at)}
                  </Form.Item>
                </>
              ) : null}
            </ProForm>
          ) : (
            !loading &&
            intl.formatMessage({
              id: 'pages.product.detail.notFound',
              defaultMessage: '未找到该商品',
            })
          )}
        </Card>

        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.images',
            defaultMessage: '商品图片',
          })}
          loading={loading}
        >
          {loading ? null : (
            <ProductImagesEditor
              images={detail?.item_img_list}
              storeId={selectedStoreId || detail?.store_id || undefined}
              alt={detail?.item_name || detail?.item_code}
              disabled={!editable}
              onChange={(next) => {
                setDetail((prev) =>
                  prev ? { ...prev, item_img_list: next } : prev,
                );
              }}
            />
          )}
        </Card>

        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.specAttrs',
            defaultMessage: '商品规格',
          })}
          loading={loading || attrsLoading}
        >
          <div style={{ marginBottom: 20 }}>
            <Typography.Text
              strong
              style={{ display: 'block', marginBottom: 12 }}
            >
              {intl.formatMessage({
                id: 'pages.product.detail.specAttrs.sectionTitle',
                defaultMessage: '规格属性',
              })}
            </Typography.Text>
            <SpecAttrsFields
              priceCategoryAttrs={priceCategoryAttrs}
              priceSelectedAttrs={priceSelectedAttrs}
              specSelfDefs={detail?.item_spec_self_def_list}
              storeId={selectedStoreId || detail?.store_id || undefined}
              disabled={!editable}
              onSpecSelfDefsChange={(next) => {
                setDetail((prev) =>
                  prev ? { ...prev, item_spec_self_def_list: next } : prev,
                );
              }}
              onValuePicChange={(attrId, attrValId, picUrl) => {
                setAttrFillValues((prev) =>
                  patchAttrValuePic(
                    prev || detail?.attr_list,
                    attrId,
                    attrValId,
                    picUrl,
                  ),
                );
                setDetail((prev) =>
                  prev
                    ? {
                        ...prev,
                        attr_list: patchAttrValuePic(
                          prev.attr_list,
                          attrId,
                          attrValId,
                          picUrl,
                        ),
                      }
                    : prev,
                );
              }}
            />
          </div>

          <Divider plain style={{ margin: '8px 0 16px' }}>
            {intl.formatMessage({
              id: 'pages.product.detail.specSku.divider',
              defaultMessage: '商品规格属性生成的规格sku',
            })}
          </Divider>

          <div>
            <Typography.Text
              strong
              style={{ display: 'block', marginBottom: 12 }}
            >
              {intl.formatMessage({
                id: 'pages.product.detail.specSku.sectionTitle',
                defaultMessage: '规格SKU',
              })}
            </Typography.Text>
            <SpecSkuTable
              skuList={detail?.sku_list}
              priceSelectedAttrs={priceSelectedAttrs}
              specSelfDefs={detail?.item_spec_self_def_list}
              itemCode={detail?.item_code}
              disabled={!editable}
              onChange={(next) => {
                setDetail((prev) =>
                  prev ? { ...prev, sku_list: next } : prev,
                );
              }}
            />
          </div>
        </Card>

        {detail?.html_content ? (
          <Card
            title={intl.formatMessage({
              id: 'pages.product.detail.section.html',
              defaultMessage: '详情描述',
            })}
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
                border: 'none',
                background: '#fff',
              }}
            />
          </Card>
        ) : null}
      </Space>
    </PageContainer>
  );
};

export default ProductDetailPage;
