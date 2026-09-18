import { PageContainer } from '@ant-design/pro-components';
import { useIntl } from '@umijs/max';
import { App, Card, Spin, Tree } from 'antd';
import type { DataNode, EventDataNode } from 'antd/es/tree';
import React, { useCallback, useEffect, useState } from 'react';
import { fetchDhSeedCategories } from '@/services/admin/categories';
import type { DhSeedCategoryPublic } from '@/types/api';

type SeedCategoryTreeNode = DataNode & {
  catePubId: string;
  isLeaf?: boolean;
};

function categoryTitle(item: DhSeedCategoryPublic): string {
  const cn = item.pub_name_cn?.trim();
  if (cn) {
    return cn;
  }
  return item.pub_name;
}

function toTreeNode(item: DhSeedCategoryPublic): SeedCategoryTreeNode {
  return {
    key: item.cate_pub_id,
    title: `${categoryTitle(item)}（${item.product_count}）`,
    catePubId: item.cate_pub_id,
    isLeaf: item.is_leaf,
  };
}

function updateTreeData(
  list: SeedCategoryTreeNode[],
  key: React.Key,
  children: SeedCategoryTreeNode[],
): SeedCategoryTreeNode[] {
  return list.map((node) => {
    if (node.key === key) {
      return {
        ...node,
        children,
        isLeaf: children.length === 0 ? true : node.isLeaf,
      };
    }
    if (node.children) {
      return {
        ...node,
        children: updateTreeData(
          node.children as SeedCategoryTreeNode[],
          key,
          children,
        ),
      };
    }
    return node;
  });
}

const ProductSeedCategory: React.FC = () => {
  const intl = useIntl();
  const { message } = App.useApp();
  const [treeData, setTreeData] = useState<SeedCategoryTreeNode[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRoot = useCallback(async () => {
    setLoading(true);
    try {
      const items = await fetchDhSeedCategories({});
      setTreeData(items.map(toTreeNode));
    } catch (error) {
      setTreeData([]);
      message.error(
        error instanceof Error
          ? error.message
          : intl.formatMessage({
              id: 'pages.product.seedCategory.loadFailed',
              defaultMessage: '加载种子商品分类失败',
            }),
      );
    } finally {
      setLoading(false);
    }
  }, [intl, message]);

  useEffect(() => {
    void loadRoot();
  }, [loadRoot]);

  const onLoadData = useCallback(
    async (treeNode: EventDataNode<SeedCategoryTreeNode>) => {
      const { key, children, catePubId, isLeaf } = treeNode;
      if (children || isLeaf) {
        return;
      }
      try {
        const items = await fetchDhSeedCategories({ parent_id: catePubId });
        const childNodes = items.map(toTreeNode);
        setTreeData((origin) => updateTreeData(origin, key, childNodes));
      } catch (error) {
        message.error(
          error instanceof Error
            ? error.message
            : intl.formatMessage({
                id: 'pages.product.seedCategory.loadChildrenFailed',
                defaultMessage: '加载子分类失败',
              }),
        );
      }
    },
    [intl, message],
  );

  return (
    <PageContainer
      title={intl.formatMessage({
        id: 'pages.product.seedCategory.title',
        defaultMessage: '种子商品分类',
      })}
    >
      <Card>
        <Spin spinning={loading}>
          {treeData.length > 0 || loading ? (
            <Tree<SeedCategoryTreeNode>
              treeData={treeData}
              loadData={onLoadData}
              blockNode
            />
          ) : (
            <div style={{ color: 'rgba(0,0,0,0.45)' }}>
              {intl.formatMessage({
                id: 'pages.product.seedCategory.empty',
                defaultMessage: '暂无种子商品分类数据',
              })}
            </div>
          )}
        </Spin>
      </Card>
    </PageContainer>
  );
};

export default ProductSeedCategory;
