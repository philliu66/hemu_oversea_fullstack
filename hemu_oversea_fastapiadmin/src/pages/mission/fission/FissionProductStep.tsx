import React from 'react';
import { ProductEditor } from '@/pages/product/detail/ProductEditor';
import type {
  DhProductDetailPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';

/**
 * 裂变第二步 / 查看变更：嵌入共用 ProductEditor。
 * 保留原 props 形状，避免抽屉调用方改动。
 */
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
  return (
    <ProductEditor
      embedded
      productId={productId}
      onDetailChange={onDetailChange}
      readOnly={readOnly}
      initialDetail={initialDetail}
      changedKeys={changedKeys}
      changedAttrList={changedAttrList}
    />
  );
}
