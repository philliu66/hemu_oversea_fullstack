import { useIntl } from '@umijs/max';
import { App, Button, Input, Modal, Select, Space, Spin, Tooltip } from 'antd';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchDhCategories,
  fetchDhCategoryPath,
  fetchDhCategorySearch,
} from '@/services/admin/categories';
import type { DhCategoryPathPublic, DhCategoryPublic } from '@/types/api';
import './categorySelectField.css';

const MAX_LEVELS = 4;

export function formatCategoryLabel(category: DhCategoryPublic): string {
  const cn = category.pub_name_cn?.trim();
  const en = category.pub_name?.trim();
  if (cn && en && cn !== en) {
    return `${cn}(${en})`;
  }
  return cn || en || category.cate_pub_id;
}

export function formatCategoryPathDisplay(path: DhCategoryPathPublic): string {
  if (path.path_items?.length) {
    return path.path_items.map(formatCategoryLabel).join(' > ');
  }
  return path.path_name;
}

type SearchHit = {
  category: DhCategoryPublic;
  pathDisplay: string;
};

type CategorySelectFieldProps = {
  /** 当前已选类目（叶子） */
  category?: DhCategoryPublic | null;
  /** 全路径文案 */
  pathDisplay?: string;
  disabled?: boolean;
  changed?: boolean;
  /** 选中叶子类目后回调（Select / 弹窗均走这里） */
  onPick: (category: DhCategoryPublic) => void;
};

function parentIdOf(category: DhCategoryPublic | null | undefined): string | null {
  const parent = category?.pare_cate_pub_id?.trim();
  return parent || null;
}

function highlightKeyword(text: string, keyword: string): React.ReactNode {
  const key = keyword.trim();
  if (!key) {
    return text;
  }
  const lower = text.toLowerCase();
  const keyLower = key.toLowerCase();
  const parts: React.ReactNode[] = [];
  let start = 0;
  let index = lower.indexOf(keyLower, start);
  let partKey = 0;
  while (index >= 0) {
    if (index > start) {
      parts.push(text.slice(start, index));
    }
    parts.push(
      <span key={`h-${partKey}`} className="hm-category-search-hit">
        {text.slice(index, index + key.length)}
      </span>,
    );
    partKey += 1;
    start = index + key.length;
    index = lower.indexOf(keyLower, start);
  }
  if (start < text.length) {
    parts.push(text.slice(start));
  }
  return parts.length ? parts : text;
}

const CategorySelectField: React.FC<CategorySelectFieldProps> = ({
  category,
  pathDisplay,
  disabled = false,
  changed = false,
  onPick,
}) => {
  const intl = useIntl();
  const { message } = App.useApp();

  const [siblingOptions, setSiblingOptions] = useState<DhCategoryPublic[]>([]);
  const [siblingsLoading, setSiblingsLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [columns, setColumns] = useState<DhCategoryPublic[][]>([]);
  const [selectedPath, setSelectedPath] = useState<DhCategoryPublic[]>([]);
  const [columnsLoading, setColumnsLoading] = useState(false);
  const [pendingLeaf, setPendingLeaf] = useState<DhCategoryPublic | null>(null);

  const [searchKeyword, setSearchKeyword] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchHits, setSearchHits] = useState<SearchHit[] | null>(null);

  const loadSiblings = useCallback(
    async (current: DhCategoryPublic | null | undefined) => {
      setSiblingsLoading(true);
      try {
        const parentId = parentIdOf(current);
        const items = await fetchDhCategories(
          parentId ? { parent_id: parentId } : {},
        );
        setSiblingOptions(items);
      } catch (error) {
        setSiblingOptions([]);
        message.error(
          error instanceof Error
            ? error.message
            : intl.formatMessage({
                id: 'pages.product.category.loadFailed',
                defaultMessage: '加载商品分类失败',
              }),
        );
      } finally {
        setSiblingsLoading(false);
      }
    },
    [intl, message],
  );

  useEffect(() => {
    void loadSiblings(category);
  }, [category?.cate_pub_id, category?.pare_cate_pub_id, loadSiblings]);

  const selectOptions = useMemo(() => {
    const map = new Map(
      siblingOptions.map((item) => [item.cate_pub_id, item]),
    );
    if (category && !map.has(category.cate_pub_id)) {
      map.set(category.cate_pub_id, category);
    }
    return Array.from(map.values()).map((item) => {
      const label = formatCategoryLabel(item);
      return {
        value: item.cate_pub_id,
        label,
        title: label,
        category: item,
      };
    });
  }, [siblingOptions, category]);

  const openModal = async () => {
    if (disabled) {
      return;
    }
    setModalOpen(true);
    setSearchKeyword('');
    setSearchHits(null);
    setPendingLeaf(null);
    setSelectedPath([]);
    setColumnsLoading(true);
    try {
      const roots = await fetchDhCategories({});
      setColumns([roots]);
    } catch (error) {
      setColumns([]);
      message.error(
        error instanceof Error
          ? error.message
          : intl.formatMessage({
              id: 'pages.product.category.loadFailed',
              defaultMessage: '加载商品分类失败',
            }),
      );
    } finally {
      setColumnsLoading(false);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    setSearchHits(null);
    setSearchKeyword('');
    setPendingLeaf(null);
  };

  const handleSelectChange = (catePubId: string | undefined) => {
    if (!catePubId) {
      return;
    }
    const option = selectOptions.find((item) => item.value === catePubId);
    if (!option) {
      return;
    }
    if (!option.category.is_leaf) {
      message.info(
        intl.formatMessage({
          id: 'pages.product.detail.categoryPickLeafHint',
          defaultMessage: '请点击「选择分类」选择到末级类目',
        }),
      );
      void openModal();
      return;
    }
    onPick(option.category);
  };

  const handleColumnClick = async (
    level: number,
    item: DhCategoryPublic,
  ) => {
    const nextPath = [...selectedPath.slice(0, level), item];
    setSelectedPath(nextPath);
    setSearchHits(null);

    if (item.is_leaf) {
      setPendingLeaf(item);
      setColumns((prev) => prev.slice(0, level + 1));
      return;
    }

    setPendingLeaf(null);
    if (level + 1 >= MAX_LEVELS) {
      // 超过四级仍非叶子时，仍允许选中当前项（尽量交给后端校验）
      setPendingLeaf(item);
      setColumns((prev) => prev.slice(0, level + 1));
      return;
    }

    setColumnsLoading(true);
    try {
      const children = await fetchDhCategories({ parent_id: item.cate_pub_id });
      if (!children.length) {
        setPendingLeaf(item);
        setColumns((prev) => prev.slice(0, level + 1));
        return;
      }
      setColumns((prev) => [...prev.slice(0, level + 1), children]);
    } catch (error) {
      message.error(
        error instanceof Error
          ? error.message
          : intl.formatMessage({
              id: 'pages.product.category.loadChildrenFailed',
              defaultMessage: '加载子分类失败',
            }),
      );
    } finally {
      setColumnsLoading(false);
    }
  };

  const handleSearch = async () => {
    const keyword = searchKeyword.trim();
    if (!keyword) {
      setSearchHits(null);
      return;
    }
    setSearching(true);
    try {
      const items = await fetchDhCategorySearch({ keyword, leaf_only: true });
      const hits = await Promise.all(
        items.map(async (item) => {
          try {
            const path = await fetchDhCategoryPath(item.id);
            return {
              category: item,
              pathDisplay: formatCategoryPathDisplay(path),
            };
          } catch {
            return {
              category: item,
              pathDisplay: formatCategoryLabel(item),
            };
          }
        }),
      );
      setSearchHits(hits);
      setPendingLeaf(null);
      setSelectedPath([]);
    } catch (error) {
      setSearchHits([]);
      message.error(
        error instanceof Error
          ? error.message
          : intl.formatMessage({
              id: 'pages.product.detail.categorySearchFailed',
              defaultMessage: '搜索分类失败',
            }),
      );
    } finally {
      setSearching(false);
    }
  };

  const confirmPick = (leaf: DhCategoryPublic | null) => {
    if (!leaf) {
      return;
    }
    onPick(leaf);
    closeModal();
  };

  const modalPathText = selectedPath.map(formatCategoryLabel).join(' > ');

  return (
    <div className="hm-category-select-field">
      <Space wrap size={8} style={{ width: '100%' }}>
        <Select
          showSearch
          allowClear={false}
          disabled={disabled}
          loading={siblingsLoading}
          value={category?.cate_pub_id}
          placeholder={intl.formatMessage({
            id: 'pages.product.detail.field.categoryPlaceholder',
            defaultMessage: '请选择分类',
          })}
          optionFilterProp="label"
          options={selectOptions}
          onChange={handleSelectChange}
          optionRender={(option) => {
            const label = String(option.label ?? '');
            return (
              <Tooltip title={label} mouseEnterDelay={0.4}>
                <span className="hm-category-select-option">{label}</span>
              </Tooltip>
            );
          }}
          className={changed ? 'hm-changed-control' : undefined}
          style={{
            maxWidth: 360,
            width: 360,
            ...(changed ? { color: '#cf1322' } : {}),
          }}
        />
        <Button type="primary" disabled={disabled} onClick={() => void openModal()}>
          {intl.formatMessage({
            id: 'pages.product.detail.categoryPickButton',
            defaultMessage: '选择分类',
          })}
        </Button>
        {pathDisplay ? (
          <Tooltip title={pathDisplay}>
            <span
              className={
                changed
                  ? 'hm-category-path-text hm-changed-text'
                  : 'hm-category-path-text'
              }
            >
              {pathDisplay}
            </span>
          </Tooltip>
        ) : null}
      </Space>

      <Modal
        title={intl.formatMessage({
          id: 'pages.product.detail.categoryModalTitle',
          defaultMessage: '选择类目',
        })}
        open={modalOpen}
        onCancel={closeModal}
        width={920}
        destroyOnClose
        footer={
          searchHits ? (
            <Button onClick={closeModal}>
              {intl.formatMessage({
                id: 'pages.product.detail.categoryModalClose',
                defaultMessage: '关闭',
              })}
            </Button>
          ) : (
            <Space>
              <Button
                type="primary"
                disabled={!pendingLeaf}
                onClick={() => confirmPick(pendingLeaf)}
              >
                {intl.formatMessage({
                  id: 'pages.product.detail.categoryModalConfirm',
                  defaultMessage: '选择',
                })}
              </Button>
              <Button onClick={closeModal}>
                {intl.formatMessage({
                  id: 'pages.product.detail.categoryModalClose',
                  defaultMessage: '关闭',
                })}
              </Button>
            </Space>
          )
        }
      >
        <div className="hm-category-modal-search">
          <Input
            allowClear
            value={searchKeyword}
            placeholder={intl.formatMessage({
              id: 'pages.product.detail.categorySearchPlaceholder',
              defaultMessage: '搜索分类名称',
            })}
            onChange={(event) => setSearchKeyword(event.target.value)}
            onPressEnter={() => void handleSearch()}
          />
          <Button type="primary" loading={searching} onClick={() => void handleSearch()}>
            {intl.formatMessage({
              id: 'pages.product.detail.categorySearchButton',
              defaultMessage: '搜索',
            })}
          </Button>
        </div>

        {!searchHits && modalPathText ? (
          <div className="hm-category-modal-path">{modalPathText}</div>
        ) : null}

        <Spin spinning={columnsLoading || searching}>
          {searchHits ? (
            <div className="hm-category-search-list">
              {searchHits.length === 0 ? (
                <div className="hm-category-empty">
                  {intl.formatMessage({
                    id: 'pages.product.detail.categorySearchEmpty',
                    defaultMessage: '未找到相关分类',
                  })}
                </div>
              ) : (
                searchHits.map((hit) => (
                  <button
                    key={hit.category.cate_pub_id}
                    type="button"
                    className="hm-category-search-item"
                    onClick={() => confirmPick(hit.category)}
                  >
                    {highlightKeyword(hit.pathDisplay, searchKeyword)}
                  </button>
                ))
              )}
            </div>
          ) : (
            <div className="hm-category-columns">
              {columns.map((col, level) => (
                <div key={`col-${level}`} className="hm-category-column">
                  <div className="hm-category-column-body">
                    {col.map((item) => {
                      const active =
                        selectedPath[level]?.cate_pub_id === item.cate_pub_id;
                      const label = formatCategoryLabel(item);
                      return (
                        <button
                          key={item.cate_pub_id}
                          type="button"
                          className={
                            active
                              ? 'hm-category-column-item is-active'
                              : 'hm-category-column-item'
                          }
                          title={label}
                          onClick={() => void handleColumnClick(level, item)}
                        >
                          <span className="hm-category-column-item-text">
                            {label}
                          </span>
                          {!item.is_leaf ? (
                            <span className="hm-category-column-item-arrow">
                              ›
                            </span>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Spin>
      </Modal>
    </div>
  );
};

export default CategorySelectField;
