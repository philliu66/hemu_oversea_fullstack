import {
  App,
  Button,
  Divider,
  Drawer,
  Input,
  Popconfirm,
  Select,
  Skeleton,
  Space,
  Typography,
} from 'antd';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import CategoryAttrsFields from '@/pages/product/detail/CategoryAttrsFields';
import CategorySelectField, {
  formatCategoryPathDisplay,
} from '@/pages/product/detail/CategorySelectField';
import {
  applyCustomAttrDraftsToAttrList,
  type CustomAttrDraft,
  mergeManagedAttrsIntoList,
  nonPriceProductAttrs,
  normalizeCustomAttrDrafts,
  retainAttrsForCategory,
  toCustomAttrDrafts,
} from '@/pages/product/detail/productFormMapping';
import {
  fetchDhCategoryAttrs,
  fetchDhCategoryPath,
} from '@/services/admin/categories';
import {
  createSkuAttrTemplate,
  deleteSkuAttrTemplate,
  fetchSkuAttrTemplateDetail,
  updateSkuAttrTemplate,
} from '@/services/admin/templates';
import type {
  DhCategoryAttrPublic,
  DhCategoryPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';

export type SkuAttrDrawerMode = 'create' | 'view' | 'edit';

type SkuOption = {
  label: string;
  value: string;
};

type SkuAttrTemplateDrawerProps = {
  open: boolean;
  mode: SkuAttrDrawerMode;
  /** 查看/编辑时的模版 ID */
  templateId?: number | null;
  skuOptions: SkuOption[];
  skuOptionsLoading?: boolean;
  onClose: () => void;
  onModeChange: (mode: SkuAttrDrawerMode) => void;
  onSaved: () => void;
};

const DH_CUSTOM_ATTR_MAX_COUNT = 20;
const DH_CUSTOM_ATTR_MAX_LENGTH = 40;

function isSaleAttr(attr: DhCategoryAttrPublic) {
  return String(attr.sale_attr) === '1';
}

function createEmptyCustomAttr(): CustomAttrDraft {
  return {
    key: `custom-new-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    attr_val_id: null,
    attr_name: '',
    content: '',
  };
}

const SkuAttrTemplateDrawer: React.FC<SkuAttrTemplateDrawerProps> = ({
  open,
  mode,
  templateId,
  skuOptions,
  skuOptionsLoading = false,
  onClose,
  onModeChange,
  onSaved,
}) => {
  const { message } = App.useApp();
  const readOnly = mode === 'view';

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [skuCode, setSkuCode] = useState<string | undefined>();
  const [pickedCategory, setPickedCategory] = useState<DhCategoryPublic | null>(
    null,
  );
  const [categoryPath, setCategoryPath] = useState<string | undefined>();
  const [categoryAttrs, setCategoryAttrs] = useState<DhCategoryAttrPublic[]>(
    [],
  );
  const [categoryAttrsLoading, setCategoryAttrsLoading] = useState(false);
  /** 类目普通属性（不含自定义 attr_id=11） */
  const [attrList, setAttrList] = useState<DhProductSelectedAttrPublic[]>([]);
  /** 自定义属性草稿（attr_id=11），保存时合并进 attr_list */
  const [customAttrs, setCustomAttrs] = useState<CustomAttrDraft[]>([]);
  const categoryAttrsReqRef = useRef(0);
  const loadedKeyRef = useRef<string>('');

  const normalCategoryAttrs = useMemo(
    () => categoryAttrs.filter((attr) => !isSaleAttr(attr)),
    [categoryAttrs],
  );

  const normalSelectedAttrs = useMemo(
    () => nonPriceProductAttrs(attrList),
    [attrList],
  );

  const loadCategoryAttrs = useCallback(async (categoryId: number) => {
    const reqId = categoryAttrsReqRef.current + 1;
    categoryAttrsReqRef.current = reqId;
    setCategoryAttrsLoading(true);
    setCategoryAttrs([]);
    try {
      const data = await fetchDhCategoryAttrs(categoryId);
      if (categoryAttrsReqRef.current !== reqId) {
        return undefined;
      }
      const list = data.attrs || [];
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

  const resetForm = useCallback(() => {
    setSkuCode(undefined);
    setPickedCategory(null);
    setCategoryPath(undefined);
    setCategoryAttrs([]);
    setAttrList([]);
    setCustomAttrs([]);
    setCategoryAttrsLoading(false);
    categoryAttrsReqRef.current += 1;
  }, []);

  const applyCategory = useCallback(
    async (
      category: DhCategoryPublic,
      options?: {
        retainAttrs?: boolean;
        nextAttrList?: DhProductSelectedAttrPublic[];
      },
    ) => {
      try {
        const pathData = await fetchDhCategoryPath(category.id);
        const selectedCategory =
          pathData.path_items[pathData.path_items.length - 1] ?? category;
        setPickedCategory(selectedCategory);
        setCategoryPath(formatCategoryPathDisplay(pathData));
        const nextCategoryAttrs = await loadCategoryAttrs(selectedCategory.id);
        if (nextCategoryAttrs === undefined) {
          return;
        }
        const allowedIds = nextCategoryAttrs.map((item) => String(item.attr_id));
        if (options?.nextAttrList) {
          const retained = retainAttrsForCategory(
            options.nextAttrList,
            allowedIds,
          );
          setCustomAttrs(toCustomAttrDrafts(options.nextAttrList));
          setAttrList(nonPriceProductAttrs(retained));
          return;
        }
        if (options?.retainAttrs) {
          setAttrList((prev) =>
            nonPriceProductAttrs(retainAttrsForCategory(prev, allowedIds)),
          );
          // 换分类时保留自定义属性草稿
        } else {
          setAttrList([]);
          setCustomAttrs([]);
        }
      } catch (error) {
        message.error(
          error instanceof Error ? error.message : '获取分类信息失败',
        );
      }
    },
    [loadCategoryAttrs, message],
  );

  useEffect(() => {
    if (!open) {
      loadedKeyRef.current = '';
      resetForm();
      return;
    }

    // 新增：仅首次打开时清空；保存并继续不重新跑加载
    if (mode === 'create' && !templateId) {
      if (loadedKeyRef.current !== 'create') {
        loadedKeyRef.current = 'create';
        resetForm();
        setLoading(false);
      }
      return;
    }

    if (!templateId) {
      return;
    }

    // 同一条详情在 view/edit 间切换时不重复拉取
    const loadKey = `detail:${templateId}`;
    if (loadedKeyRef.current === loadKey) {
      return;
    }
    loadedKeyRef.current = loadKey;

    let cancelled = false;
    void (async () => {
      setLoading(true);
      try {
        const detail = await fetchSkuAttrTemplateDetail(templateId);
        if (cancelled) {
          return;
        }
        setSkuCode(detail.sku_code);
        const nextAttrs = (detail.raw_json?.attr_list ||
          []) as DhProductSelectedAttrPublic[];
        if (detail.category_id) {
          await applyCategory(
            {
              id: detail.category_id,
              cate_pub_id: detail.cate_pub_id,
              pub_name: detail.cate_name || detail.cate_pub_id,
              pub_name_cn: detail.cate_name || null,
              leaf: '1',
              pare_cate_pub_id: null,
              is_leaf: true,
              remark: null,
            },
            { nextAttrList: nextAttrs },
          );
        } else {
          setPickedCategory(null);
          setCategoryPath(detail.cate_name || detail.cate_pub_id);
          setCustomAttrs(toCustomAttrDrafts(nextAttrs));
          setAttrList(nonPriceProductAttrs(nextAttrs));
        }
      } catch (error) {
        if (!cancelled) {
          message.error(
            error instanceof Error ? error.message : '加载属性模板失败',
          );
          onClose();
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
  }, [open, mode, templateId, applyCategory, resetForm, message, onClose]);

  const handleCategoryPick = (picked: DhCategoryPublic) => {
    void applyCategory(picked, { retainAttrs: true });
  };

  const validateBeforeSave = () => {
    if (!skuCode) {
      message.warning('请选择产品型号');
      return false;
    }
    if (!pickedCategory?.cate_pub_id) {
      message.warning('请选择商品分类');
      return false;
    }
    return true;
  };

  const buildPayload = () => ({
    sku_code: skuCode!,
    cate_pub_id: pickedCategory!.cate_pub_id,
    raw_json: {
      attr_list: applyCustomAttrDraftsToAttrList(
        attrList,
        normalizeCustomAttrDrafts(customAttrs),
      ),
    },
  });

  const handleSave = async (continueCreate: boolean) => {
    if (!validateBeforeSave()) {
      return;
    }
    setSaving(true);
    try {
      const payload = buildPayload();
      if (mode === 'create' || !templateId) {
        await createSkuAttrTemplate(payload);
        message.success('创建成功');
        onSaved();
        if (continueCreate) {
          // 清空已选属性值、自定义属性与 SKU，保留分类与属性定义列表
          setSkuCode(undefined);
          setAttrList([]);
          setCustomAttrs([]);
          onModeChange('create');
        } else {
          onClose();
        }
        return;
      }
      await updateSkuAttrTemplate({ id: templateId, ...payload });
      message.success('保存成功');
      onSaved();
      onClose();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const title =
    mode === 'create'
      ? '新增属性模板'
      : mode === 'edit'
        ? '编辑属性模板'
        : '查看属性';

  const footer =
    mode === 'view' ? (
      <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
        <Popconfirm
          title="确认删除该属性模板？"
          onConfirm={async () => {
            if (!templateId) {
              return;
            }
            try {
              await deleteSkuAttrTemplate(templateId);
              message.success('删除成功');
              onSaved();
              onClose();
            } catch {
              // 错误已由全局拦截器处理
            }
          }}
        >
          <Button danger>删除</Button>
        </Popconfirm>
        <Button type="primary" onClick={() => onModeChange('edit')}>
          编辑
        </Button>
      </Space>
    ) : mode === 'create' ? (
      <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
        <Button onClick={onClose}>取消</Button>
        <Button loading={saving} onClick={() => void handleSave(true)}>
          保存并继续
        </Button>
        <Button
          type="primary"
          loading={saving}
          onClick={() => void handleSave(false)}
        >
          保存
        </Button>
      </Space>
    ) : (
      <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
        <Button
          onClick={() => {
            if (templateId) {
              // 丢弃未保存修改，回到查看态并重新拉取
              loadedKeyRef.current = '';
              onModeChange('view');
            } else {
              onClose();
            }
          }}
        >
          取消
        </Button>
        <Button
          type="primary"
          loading={saving}
          onClick={() => void handleSave(false)}
        >
          保存
        </Button>
      </Space>
    );

  return (
    <Drawer
      title={title}
      width={720}
      open={open}
      onClose={onClose}
      destroyOnHidden
      maskClosable={false}
      footer={footer}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <div>
            <Typography.Text
              strong
              style={{ display: 'block', marginBottom: 8 }}
            >
              产品型号
            </Typography.Text>
            <Select
              showSearch
              allowClear
              placeholder="请选择产品型号"
              style={{ width: '100%' }}
              options={skuOptions}
              value={skuCode}
              disabled={readOnly}
              loading={skuOptionsLoading}
              optionFilterProp="label"
              onChange={(value) => setSkuCode(value)}
            />
          </div>
          <div>
            <Typography.Text
              strong
              style={{ display: 'block', marginBottom: 8 }}
            >
              商品分类
            </Typography.Text>
            <CategorySelectField
              category={pickedCategory}
              pathDisplay={categoryPath}
              disabled={readOnly}
              onPick={handleCategoryPick}
            />
          </div>
          <div>
            <Typography.Text
              strong
              style={{ display: 'block', marginBottom: 12 }}
            >
              类目属性
            </Typography.Text>
            {categoryAttrsLoading ? (
              <Skeleton active paragraph={{ rows: 6 }} />
            ) : !pickedCategory ? (
              <Typography.Text type="secondary">
                请先选择商品分类
              </Typography.Text>
            ) : normalCategoryAttrs.length === 0 ? (
              <Typography.Text type="secondary">暂无类目属性</Typography.Text>
            ) : (
              <CategoryAttrsFields
                attrs={normalCategoryAttrs}
                selectedAttrs={normalSelectedAttrs}
                disabled={readOnly}
                onSelectedAttrsChange={
                  readOnly
                    ? undefined
                    : (nextSelected) => {
                        const managedIds = normalCategoryAttrs.map((item) =>
                          String(item.attr_id),
                        );
                        setAttrList((prev) =>
                          mergeManagedAttrsIntoList(
                            prev,
                            managedIds,
                            nextSelected,
                          ),
                        );
                      }
                }
              />
            )}
            <Divider />
            <Typography.Text
              strong
              style={{ display: 'block', marginBottom: 8 }}
            >
              自定义属性
            </Typography.Text>
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              {customAttrs.map((row, index) => (
                <Space key={row.key} size={8} wrap align="center">
                  <Input
                    placeholder="请输入属性名"
                    maxLength={DH_CUSTOM_ATTR_MAX_LENGTH}
                    allowClear
                    disabled={readOnly}
                    value={row.attr_name}
                    style={{ width: 220 }}
                    onChange={(event) => {
                      const value = event.target.value;
                      setCustomAttrs((prev) =>
                        prev.map((item, i) =>
                          i === index ? { ...item, attr_name: value } : item,
                        ),
                      );
                    }}
                  />
                  <Input
                    placeholder="请输入属性值"
                    maxLength={DH_CUSTOM_ATTR_MAX_LENGTH}
                    allowClear
                    disabled={readOnly}
                    value={row.content}
                    style={{ width: 320 }}
                    onChange={(event) => {
                      const value = event.target.value;
                      setCustomAttrs((prev) =>
                        prev.map((item, i) =>
                          i === index ? { ...item, content: value } : item,
                        ),
                      );
                    }}
                  />
                  {readOnly ? null : (
                    <Button
                      type="link"
                      danger
                      onClick={() => {
                        setCustomAttrs((prev) =>
                          prev.filter((_, i) => i !== index),
                        );
                      }}
                    >
                      删除
                    </Button>
                  )}
                </Space>
              ))}
              {readOnly ? null : (
                <Button
                  type="dashed"
                  disabled={customAttrs.length >= DH_CUSTOM_ATTR_MAX_COUNT}
                  style={{ width: '100%', maxWidth: 720 }}
                  onClick={() => {
                    setCustomAttrs((prev) => [...prev, createEmptyCustomAttr()]);
                  }}
                >
                  新增属性
                </Button>
              )}
            </Space>
          </div>
        </Space>
      )}
    </Drawer>
  );
};

export default SkuAttrTemplateDrawer;
