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
import React, { useCallback, useEffect, useRef, useState } from 'react';
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
  fetchDhCategories,
  fetchDhCategoryAttrs,
  fetchDhCategoryPath,
} from '@/services/admin/categories';
import {
  fetchDhProductDetail,
  fetchDhProductGroupList,
} from '@/services/admin/products';
import {
  fetchStoreAftersaleTemplates,
  fetchStoreList,
  fetchStoreShippingTemplates,
} from '@/services/admin/stores';
import type {
  DhCategoryAttrPublic,
  DhCategoryPathPublic,
  DhCategoryPublic,
  DhProductDetailPublic,
  DhProductGroupPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';
import { formatDateTime } from '@/utils/datetime';

const ITEM_NAME_MAX_LENGTH = 140;
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

type ItemGroupCascaderOption = DefaultOptionType & {
  value: string;
  label: string;
  isLeaf?: boolean;
  children?: ItemGroupCascaderOption[];
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
}: {
  productId: number;
  onDetailChange: (detail: DhProductDetailPublic) => void;
}) {
  const intl = useIntl();
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const supplierId = initialState?.currentUser?.supplier_id;
  const [form] = Form.useForm<ProductFormValues>();
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
  const [aftersaleOptions, setAftersaleOptions] = useState<TemplateOption[]>(
    [],
  );
  const [shippingOptions, setShippingOptions] = useState<TemplateOption[]>([]);
  const itemGroupLoadedRef = useRef(false);

  const publishDetail = useCallback((next: DhProductDetailPublic) => {
    setDetail(next);
    onDetailChangeRef.current(next);
  }, []);

  const patchDetail = useCallback((patch: Partial<DhProductDetailPublic>) => {
    setDetail((prev) => {
      if (!prev) {
        return prev;
      }
      const next = { ...prev, ...patch };
      onDetailChangeRef.current(next);
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
        const data = await fetchDhProductDetail(productId);
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
          item_group_path: data.item_group_id
            ? [data.item_group_id]
            : undefined,
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
  }, [intl, message, productId, publishDetail]);

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

  const loadItemGroups = useCallback(async () => {
    if (!detail?.store_id || itemGroupLoadedRef.current) {
      return;
    }
    const data = await fetchDhProductGroupList({
      store_id: detail.store_id,
      page: 1,
      page_size: 100,
    });
    const options = data.items
      .filter((item) => Boolean(item.group_id))
      .map((item) => toItemGroupCascaderOption(item));
    itemGroupLoadedRef.current = true;
    setItemGroupOptions(options);
    const currentId = detail.item_group_id;
    if (currentId) {
      const path = findItemGroupPath(options, currentId);
      if (path) {
        form.setFieldValue('item_group_path', path);
      }
    }
  }, [detail?.item_group_id, detail?.store_id]);

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
          onDetailChangeRef.current(next);
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

  const syncFormValues = (values: ProductFormValues) => {
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
        attr_list: applyCustomAttrDraftsToAttrList(
          prev.attr_list,
          values.customAttrs || [],
        ),
      };
      onDetailChangeRef.current(next);
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

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <ProForm<ProductFormValues>
        key={productId}
        form={form}
        submitter={false}
        layout="horizontal"
        labelAlign="left"
        labelCol={{ flex: '110px' }}
        wrapperCol={{ flex: 1 }}
        onValuesChange={(_, values) => {
          if ('store_id' in _) {
            itemGroupLoadedRef.current = false;
            setItemGroupOptions([]);
          }
          syncFormValues(values);
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
            label={intl.formatMessage({
              id: 'pages.product.detail.field.storeName',
              defaultMessage: '店铺名称',
            })}
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
            fieldProps={{ style: { maxWidth: 360 } }}
          />
          <Form.Item
            name="category_path"
            label={intl.formatMessage({
              id: 'pages.product.detail.field.productCategory',
              defaultMessage: '产品分类',
            })}
          >
            <Cascader
              options={cascaderOptions}
              loadData={loadCategoryData}
              onChange={onCategoryChange}
              changeOnSelect={false}
              displayRender={(labels) => labels.at(-1) ?? ''}
              placeholder={intl.formatMessage({
                id: 'pages.product.detail.field.categoryPlaceholder',
                defaultMessage: '请选择分类',
              })}
              style={{ maxWidth: 480, width: '100%' }}
            />
          </Form.Item>
          {categoryPath ? (
            <Typography.Text
              style={{
                display: 'block',
                margin: '-8px 0 16px 110px',
                color: '#a0522d',
              }}
            >
              {categoryPath}
            </Typography.Text>
          ) : null}
        </Card>

        <Card
          title={intl.formatMessage({
            id: 'pages.product.detail.section.attrs',
            defaultMessage: '商品属性',
          })}
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
            style={{ display: 'block', marginBottom: 12 }}
          >
            {intl.formatMessage({
              id: 'pages.product.detail.customAttrs.title',
              defaultMessage: '自定义属性',
            })}
          </Typography.Text>
          <ProFormList
            name="customAttrs"
            copyIconProps={false}
            creatorButtonProps={{
              creatorButtonText: intl.formatMessage({
                id: 'pages.product.detail.customAttrs.add',
                defaultMessage: '新增属性',
              }),
              type: 'dashed',
              style: { width: '100%', maxWidth: 720 },
            }}
            max={DH_CUSTOM_ATTR_MAX_COUNT}
            creatorRecord={() => ({
              key: `custom-new-${Date.now()}`,
              attr_val_id: null,
              attr_name: '',
              content: '',
            })}
          >
            <Space size={8} wrap>
              <ProFormText name="key" hidden />
              <ProFormText name="attr_val_id" hidden />
              <ProFormText
                name="attr_name"
                fieldProps={{
                  maxLength: DH_CUSTOM_ATTR_MAX_LENGTH,
                  style: { width: 220 },
                }}
                formItemProps={{ style: { marginBottom: 0 } }}
              />
              <ProFormText
                name="content"
                fieldProps={{
                  maxLength: DH_CUSTOM_ATTR_MAX_LENGTH,
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
            label={intl.formatMessage({
              id: 'pages.product.detail.field.itemName',
              defaultMessage: '产品标题',
            })}
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
            <Space size={12} wrap>
              <Form.Item name="key_word1" noStyle>
                <Input allowClear style={{ width: 240 }} />
              </Form.Item>
              <Form.Item name="key_word2" noStyle>
                <Input allowClear style={{ width: 240 }} />
              </Form.Item>
              <Form.Item name="key_word3" noStyle>
                <Input allowClear style={{ width: 240 }} />
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
              style={{ maxWidth: 480, width: '100%' }}
              placeholder={intl.formatMessage({
                id: 'pages.product.detail.field.itemGroupPlaceholder',
                defaultMessage: '请选择产品分组',
              })}
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
        title={intl.formatMessage({
          id: 'pages.product.detail.section.images',
          defaultMessage: '商品图片',
        })}
        loading={loading}
      >
        {loading ? null : (
          <ProductImagesEditor
            images={detail?.item_img_list}
            storeId={detail?.store_id || undefined}
            alt={detail?.item_name || detail?.item_code}
            onChange={(next) => {
              setDetail((prev) => {
                if (!prev) {
                  return prev;
                }
                const updated = { ...prev, item_img_list: next };
                onDetailChangeRef.current(updated);
                return updated;
              });
            }}
          />
        )}
      </Card>

      <Card
        title={intl.formatMessage({
          id: 'pages.product.detail.section.specAttrs',
          defaultMessage: '商品规格',
        })}
        loading={loading}
      >
        <SpecAttrsFields
          priceCategoryAttrs={priceCategoryAttrs}
          priceSelectedAttrs={priceSelectedAttrs}
          specSelfDefs={detail?.item_spec_self_def_list}
          storeId={detail?.store_id || undefined}
          onSpecSelfDefsChange={(next) => {
            setDetail((prev) => {
              if (!prev) {
                return prev;
              }
              const updated = { ...prev, item_spec_self_def_list: next };
              onDetailChangeRef.current(updated);
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
              onDetailChangeRef.current(updated);
              return updated;
            });
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

      <Card
        title={intl.formatMessage({
          id: 'pages.product.detail.section.templates',
          defaultMessage: '模板信息',
        })}
        loading={loading}
      >
        <div style={{ maxWidth: 720 }}>
          <div style={{ display: 'flex', marginBottom: 24 }}>
            <div style={{ width: 110, flex: '0 0 110px', lineHeight: '32px' }}>
              {intl.formatMessage({
                id: 'pages.product.detail.field.afterSaleTemplate',
                defaultMessage: '售后模板',
              })}
            </div>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              style={{ maxWidth: 360, width: '100%' }}
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
            <div style={{ width: 110, flex: '0 0 110px', lineHeight: '32px' }}>
              {intl.formatMessage({
                id: 'pages.product.detail.field.shippingTemplate',
                defaultMessage: '物流模板',
              })}
            </div>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              style={{ maxWidth: 360, width: '100%' }}
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
