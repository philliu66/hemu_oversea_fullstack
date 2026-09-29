import { useLocation } from '@umijs/max';
import React, { useMemo } from 'react';
import { resolveProductPageRoute } from '../utils';
import { ProductEditor } from './ProductEditor';

/**
 * 商品详情 / 编辑 / 新建 / 复制：共用 ProductEditor。
 * 模式由路由解析（/product/detail|edit|create）。
 */
const ProductDetailPage: React.FC = () => {
  const location = useLocation();
  const routeState = useMemo(
    () => resolveProductPageRoute(location.pathname, location.search),
    [location.pathname, location.search],
  );

  return (
    <ProductEditor
      mode={routeState.mode}
      productId={routeState.productId}
      fromId={routeState.fromId}
    />
  );
};

export default ProductDetailPage;
