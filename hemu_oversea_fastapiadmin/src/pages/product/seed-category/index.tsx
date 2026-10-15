import { PageContainer } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import { App, Card, Empty, Space, Spin, Tabs, Tree } from 'antd';
import type { DataNode, EventDataNode } from 'antd/es/tree';
import React, { useCallback, useEffect, useState } from 'react';
import SupplierSelectField from '@/components/SupplierSelectField';
import { fetchDhSeedCategories } from '@/services/admin/categories';
import type { DhSeedCategoryPublic } from '@/types/api';
import {
  needsSupplierSelection,
  resolveRequestSupplierId,
} from '@/utils/portalScope';

type SeedCategoryTreeNode = DataNode & {
  catePubId: string;
  isLeaf?: boolean;
};

type PlatformTabKey = 'dhgate' | 'tiktok';

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

const DhgateSeedCategoryTree: React.FC<{ supplierId?: number }> = ({
  supplierId,
}) => {
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const [treeData, setTreeData] = useState<SeedCategoryTreeNode[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRoot = useCallback(async () => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      setTreeData([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const items = await fetchDhSeedCategories({ supplier_id: supplierId });
      setTreeData(items.map(toTreeNode));
    } catch (error) {
      setTreeData([]);
      message.error(
        error instanceof Error
          ? error.message
          : '加载种子商品分类失败',
      );
    } finally {
      setLoading(false);
    }
  }, [currentUser, message, supplierId]);

  useEffect(() => {
    void loadRoot();
  }, [loadRoot]);

  const onLoadData = useCallback(
    async (treeNode: EventDataNode<SeedCategoryTreeNode>) => {
      const { key, children, catePubId, isLeaf } = treeNode;
      if (children || isLeaf || !supplierId) {
        return;
      }
      try {
        const items = await fetchDhSeedCategories({
          parent_id: catePubId,
          supplier_id: supplierId,
        });
        const childNodes = items.map(toTreeNode);
        setTreeData((origin) => updateTreeData(origin, key, childNodes));
      } catch (error) {
        message.error(
          error instanceof Error
            ? error.message
            : '加载子分类失败',
        );
      }
    },
    [message, supplierId],
  );

  if (needsSupplierSelection(currentUser, supplierId)) {
    return (
      <div style={{ color: 'rgba(0,0,0,0.45)' }}>
        {'请先选择供应商'}
      </div>
    );
  }

  return (
    <Spin spinning={loading}>
      {treeData.length > 0 || loading ? (
        <Tree<SeedCategoryTreeNode>
          treeData={treeData}
          loadData={onLoadData}
          blockNode
        />
      ) : (
        <div style={{ color: 'rgba(0,0,0,0.45)' }}>
          {'暂无种子商品分类数据'}
        </div>
      )}
    </Spin>
  );
};

const ProductSeedCategory: React.FC = () => {
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const [activeTab, setActiveTab] = useState<PlatformTabKey>('dhgate');
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();
  const supplierId = resolveRequestSupplierId(currentUser, selectedSupplierId);

  return (
    <PageContainer title={'种子商品分类'}>
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as PlatformTabKey)}
          items={[
            {
              key: 'dhgate',
              label: '敦煌',
              children: (
                <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                  {access.canPlatform ? (
                    <div style={{ maxWidth: 360 }}>
                      <SupplierSelectField
                        value={selectedSupplierId}
                        onChange={(v) => setSelectedSupplierId(v)}
                      />
                    </div>
                  ) : null}
                  <DhgateSeedCategoryTree supplierId={supplierId} />
                </Space>
              ),
            },
            {
              key: 'tiktok',
              label: 'TikTok',
              children: (
                <Empty description={'TikTok 商品分类暂未接入'} />
              ),
            },
          ]}
        />
      </Card>
    </PageContainer>
  );
};

export default ProductSeedCategory;
