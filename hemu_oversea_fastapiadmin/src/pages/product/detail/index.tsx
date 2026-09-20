import type { ProColumns, ProFormInstance } from '@ant-design/pro-components';
import {
  PageContainer,
  ProForm,
  ProFormSelect,
  ProTable,
} from '@ant-design/pro-components';
import { history, useIntl, useModel, useParams } from '@umijs/max';
import {
  App,
  Card,
  Cascader,
  Form,
  Image,
  Input,
  Space,
  Tag,
  Typography,
} from 'antd';
import type { CascaderProps, DefaultOptionType } from 'antd/es/cascader';
import React, {
  useCallback,
  useEffect,
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
  DhProductSkuPublic,
  DhProductSpecSelfDefPublic,
} from '@/types/api';
import {
  DH_PRODUCT_STATE_LABEL,
  DH_PRODUCT_STATES,
  type DhProductStateCode,
} from '@/constants/product';
import { formatDateTime } from '@/utils/datetime';
import { buildDhImageUrl } from '@/utils/dhImage';
import { PRODUCT_LIST_PATH, parseProductId } from '../utils';
import CategoryAttrsFields from './CategoryAttrsFields';
import ProductImagesEditor from './ProductImagesEditor';

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

function isCustomProductAttr(attr: DhProductSelectedAttrPublic) {
  return String(attr.attr_id) === DH_CUSTOM_PRODUCT_ATTR_ID;
}

function categoryProductAttrs(list?: DhProductSelectedAttrPublic[]) {
  return (list || []).filter((item) => !isCustomProductAttr(item));
}

function customProductAttrValues(list?: DhProductSelectedAttrPublic[]) {
  return (list || [])
    .filter(isCustomProductAttr)
    .flatMap((item) => item.values || []);
}

type CustomAttrDraft = {
  key: string;
  attr_val_id: string;
  attr_name: string;
  content: string;
};

function toCustomAttrDrafts(
  list?: DhProductSelectedAttrPublic[],
): CustomAttrDraft[] {
  return customProductAttrValues(list).map((item, index) => ({
    key: item.attr_val_id || `custom-${index}`,
    attr_val_id: item.attr_val_id,
    attr_name: (item.attr_name_cn || item.attr_name || '').trim(),
    content: (
      item.line_attrval_name_cn ||
      item.line_attrval_name ||
      ''
    ).trim(),
  }));
}

function formatPrice(value: string | number | null | undefined): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  const num = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(num)) {
    return String(value);
  }
  return num.toFixed(2);
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
  formatLabel: (name: string, count: number) => string,
): ItemGroupCascaderOption {
  const children = (group.children || [])
    .filter((item) => Boolean(item.group_id))
    .map((item) => toItemGroupCascaderOption(item, formatLabel));
  return {
    value: group.group_id,
    label: formatLabel(groupDisplayName(group), group.item_count ?? 0),
    isLeaf: children.length === 0,
    children: children.length ? children : undefined,
  };
}

function toItemGroupCascaderOptions(
  groups: DhProductGroupPublic[],
  formatLabel: (name: string, count: number) => string,
): ItemGroupCascaderOption[] {
  return groups
    .filter((item) => Boolean(item.group_id))
    .map((item) => toItemGroupCascaderOption(item, formatLabel));
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

const ProductDetailPage: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const supplierId = initialState?.currentUser?.supplier_id;
  const { id: idParam } = useParams<{ id: string }>();
  const productId = parseProductId(idParam);
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

  const formatItemGroupLabel = useCallback(
    (name: string, count: number) =>
      intl.formatMessage(
        {
          id: 'pages.product.detail.field.itemGroupOption',
          defaultMessage: '{name}（{count}）',
        },
        { name, count },
      ),
    [intl],
  );

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
      const options = toItemGroupCascaderOptions(
        data.items,
        formatItemGroupLabel,
      );
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
  }, [detail?.item_group_id, detail?.store_id, formatItemGroupLabel, intl, message]);

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
    if (!productId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchDhProductDetail(productId);
      let nextCategoryPath: string[] | undefined;
      let nextOptions: CategoryOption[] = [];

      if (data.category?.id) {
        try {
          const pathData = await applyCategoryPath(data.category.id);
          nextCategoryPath = pathData.path_items.map((item) => item.cate_pub_id);
          nextOptions = await loadCascaderOptionsAlongPath(pathData.path_items);
        } catch (pathError) {
          setCategoryPath(formatCategoryLabel(data.category));
          nextOptions = (await fetchDhCategories({})).map(toCascaderOption);
          const fallbackId = data.cate_pub_id || data.category.cate_pub_id;
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
      setSelectedStoreId(data.store_id);
      setDetail(data);
      setCustomAttrDrafts(toCustomAttrDrafts(data.attr_list));
      originalCategoryIdRef.current = data.category?.id;
      await loadCategoryAttrs(
        data.category?.id,
        categoryProductAttrs(data.attr_list),
      );
    } catch (error) {
      setDetail(undefined);
      setSelectedStoreId(undefined);
      setCategoryPath(undefined);
      setCascaderOptions([]);
      setInitialCategoryPath(undefined);
      setCategoryAttrs([]);
      setAttrFillValues(undefined);
      setCustomAttrDrafts([]);
      originalCategoryIdRef.current = undefined;
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
  }, [applyCategoryPath, intl, loadCategoryAttrs, message, productId]);

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
        setItemGroupOptions([
          toItemGroupCascaderOption(group, formatItemGroupLabel),
        ]);
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
  }, [detail?.item_group_id, detail?.store_id, formatItemGroupLabel]);

  const patchCustomAttrDraft = (
    key: string,
    patch: Partial<Pick<CustomAttrDraft, 'attr_name' | 'content'>>,
  ) => {
    setCustomAttrDrafts((prev) =>
      prev.map((item) => (item.key === key ? { ...item, ...patch } : item)),
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

  const specSelfDefColumns: ProColumns<DhProductSpecSelfDefPublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.specSelfDef.pic',
        defaultMessage: '图片',
      }),
      dataIndex: 'pic_url',
      width: 72,
      search: false,
      render: (_, record) =>
        record.pic_url ? (
          <Image
            src={record.pic_url}
            alt={record.attr_val_name || record.attr_val_id || 'spec'}
            width={40}
            height={40}
            style={{ objectFit: 'cover', borderRadius: 4 }}
          />
        ) : (
          '-'
        ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.specSelfDef.specAttrName',
        defaultMessage: '规格名称',
      }),
      dataIndex: 'spec_attr_name',
      width: 160,
      ellipsis: true,
      search: false,
      render: (_, record) => record.spec_attr_name || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.specSelfDef.attrValName',
        defaultMessage: '规格值',
      }),
      dataIndex: 'attr_val_name',
      ellipsis: true,
      search: false,
      render: (_, record) => record.attr_val_name || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.specSelfDef.attrValId',
        defaultMessage: '规格值 ID',
      }),
      dataIndex: 'attr_val_id',
      width: 140,
      ellipsis: true,
      search: false,
      render: (_, record) => record.attr_val_id || '-',
    },
  ];

  const skuColumns: ProColumns<DhProductSkuPublic>[] = [
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.sku.pic',
        defaultMessage: '图片',
      }),
      dataIndex: 'pic_url',
      width: 72,
      search: false,
      render: (_, record) =>
        record.pic_url ? (
          <Image
            src={record.pic_url}
            alt={record.sku_code || record.sku_id || 'sku'}
            width={40}
            height={40}
            style={{ objectFit: 'cover', borderRadius: 4 }}
          />
        ) : (
          '-'
        ),
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.sku.attr',
        defaultMessage: '规格',
      }),
      dataIndex: 'attr_combo_text',
      ellipsis: true,
      search: false,
      render: (_, record) => record.attr_combo_text || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.sku.code',
        defaultMessage: 'SKU 编码',
      }),
      dataIndex: 'sku_code',
      width: 140,
      ellipsis: true,
      search: false,
      render: (_, record) => record.sku_code || record.sku_id || '-',
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.sku.price',
        defaultMessage: '零售价',
      }),
      dataIndex: 'retail_price',
      width: 100,
      align: 'right',
      search: false,
      render: (_, record) => formatPrice(record.retail_price),
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.sku.inventory',
        defaultMessage: '库存',
      }),
      dataIndex: 'inventory',
      width: 90,
      align: 'right',
      search: false,
      render: (_, record) =>
        record.inventory === null || record.inventory === undefined
          ? '-'
          : record.inventory,
    },
    {
      title: intl.formatMessage({
        id: 'pages.product.detail.sku.saleStatus',
        defaultMessage: '可售',
      }),
      dataIndex: 'sale_status',
      width: 90,
      search: false,
      render: (_, record) => {
        if (record.sale_status === '1') {
          return (
            <Tag color="success">
              {intl.formatMessage({
                id: 'pages.product.detail.sku.saleYes',
                defaultMessage: '可售',
              })}
            </Tag>
          );
        }
        if (record.sale_status === '0') {
          return (
            <Tag>
              {intl.formatMessage({
                id: 'pages.product.detail.sku.saleNo',
                defaultMessage: '不可售',
              })}
            </Tag>
          );
        }
        return '-';
      },
    },
  ];

  if (!productId) {
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

  return (
    <PageContainer title={false} onBack={() => history.push(PRODUCT_LIST_PATH)}>
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
              key={detail.id}
              formRef={formRef}
              submitter={false}
              layout="horizontal"
              labelCol={{ flex: '110px' }}
              wrapperCol={{ flex: 1 }}
              style={{ maxWidth: 720 }}
              initialValues={{
                store_id: detail.store_id,
                category_path: initialCategoryPath,
              }}
              onValuesChange={(changed) => {
                if ('store_id' in changed) {
                  setSelectedStoreId(changed.store_id);
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
                    // 限制每列宽度，长文案省略，避免多级菜单横向撑出视口
                    popupMenuColumnStyle={{
                      width: 180,
                      maxWidth: 180,
                    }}
                    styles={{
                      popup: {
                        root: {
                          maxWidth: 'min(100vw - 24px, 560px)',
                          overflowX: 'auto',
                        },
                        listItem: {
                          maxWidth: 180,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        },
                      },
                    }}
                    optionRender={(option) => (
                      <span title={String(option.label ?? '')}>
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
            defaultMessage: '属性信息',
          })}
          loading={loading || attrsLoading}
        >
          {categoryAttrs.length > 0 ? (
            <CategoryAttrsFields
              attrs={categoryAttrs}
              selectedAttrs={attrFillValues}
            />
          ) : null}
          {customAttrDrafts.length > 0 ? (
            <div
              style={{
                marginTop: categoryAttrs.length > 0 ? 16 : 0,
              }}
            >
              <Typography.Text
                strong
                style={{ display: 'block', marginBottom: 8 }}
              >
                {intl.formatMessage({
                  id: 'pages.product.detail.customAttrs.title',
                  defaultMessage: '自定义属性',
                })}
              </Typography.Text>
              <table
                style={{
                  borderCollapse: 'collapse',
                  maxWidth: 640,
                  width: '100%',
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr>
                    <th
                      style={{
                        border: '1px solid #d9d9d9',
                        background: '#fafafa',
                        padding: '6px 10px',
                        fontWeight: 500,
                        width: 200,
                        textAlign: 'left',
                      }}
                    >
                      {intl.formatMessage({
                        id: 'pages.product.detail.customAttrs.name',
                        defaultMessage: '属性名',
                      })}
                    </th>
                    <th
                      style={{
                        border: '1px solid #d9d9d9',
                        background: '#fafafa',
                        padding: '6px 10px',
                        fontWeight: 500,
                        textAlign: 'left',
                      }}
                    >
                      {intl.formatMessage({
                        id: 'pages.product.detail.customAttrs.value',
                        defaultMessage: '属性值',
                      })}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {customAttrDrafts.map((item) => (
                    <tr key={item.key}>
                      <td
                        style={{
                          border: '1px solid #d9d9d9',
                          padding: 6,
                        }}
                      >
                        <Input
                          value={item.attr_name}
                          allowClear
                          placeholder={intl.formatMessage({
                            id: 'pages.product.detail.attrsCustomNamePlaceholder',
                            defaultMessage: '请输入属性名',
                          })}
                          onChange={(event) =>
                            patchCustomAttrDraft(item.key, {
                              attr_name: event.target.value,
                            })
                          }
                        />
                      </td>
                      <td
                        style={{
                          border: '1px solid #d9d9d9',
                          padding: 6,
                        }}
                      >
                        <Input
                          value={item.content}
                          allowClear
                          placeholder={intl.formatMessage({
                            id: 'pages.product.detail.attrsCustomValuePlaceholder',
                            defaultMessage: '请输入属性值',
                          })}
                          onChange={(event) =>
                            patchCustomAttrDraft(item.key, {
                              content: event.target.value,
                            })
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {categoryAttrs.length === 0 &&
          customAttrDrafts.length === 0 &&
          !loading &&
          !attrsLoading
            ? intl.formatMessage({
                id: 'pages.product.detail.attrsEmpty',
                defaultMessage: '暂无属性',
              })
            : null}
        </Card>

        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.specSelfDef',
            defaultMessage: '自定义规格',
          })}
          loading={loading}
        >
          <ProTable<DhProductSpecSelfDefPublic>
            rowKey={(record) =>
              [
                record.attr_val_id,
                record.spec_attr_name,
                record.attr_val_name,
                record.pic_url,
              ]
                .filter(Boolean)
                .join('|') || 'spec'
            }
            search={false}
            options={false}
            toolBarRender={false}
            pagination={false}
            dataSource={detail?.item_spec_self_def_list || []}
            columns={specSelfDefColumns}
            size="small"
            scroll={{ x: 560 }}
            locale={{
              emptyText: intl.formatMessage({
                id: 'pages.product.detail.specSelfDef.empty',
                defaultMessage: '暂无自定义规格',
              }),
            }}
          />
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
              key={`product-info-${detail.id}`}
              formRef={productInfoFormRef}
              submitter={false}
              layout="horizontal"
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
              <Form.Item
                label={intl.formatMessage({
                  id: 'pages.product.detail.field.productState',
                  defaultMessage: '商品状态',
                })}
              >
                {formatProductState(detail.state, (id, defaultMessage) =>
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
              storeId={selectedStoreId ?? detail?.store_id}
              alt={detail?.item_name || detail?.item_code}
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
            id: 'pages.product.detail.section.sku',
            defaultMessage: 'SKU 列表',
          })}
          loading={loading}
        >
          <ProTable<DhProductSkuPublic>
            rowKey="id"
            search={false}
            options={false}
            toolBarRender={false}
            pagination={false}
            dataSource={detail?.sku_list || []}
            columns={skuColumns}
            size="small"
            scroll={{ x: 720 }}
            locale={{
              emptyText: intl.formatMessage({
                id: 'pages.product.detail.skuEmpty',
                defaultMessage: '暂无 SKU',
              }),
            }}
          />
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
