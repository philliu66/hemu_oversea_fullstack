import React, { forwardRef } from 'react';
import {
  ProductEditor,
  type ProductEditorHandle,
} from '@/pages/product/detail/ProductEditor';
import type {
  DhProductDetailPublic,
  DhProductSelectedAttrPublic,
} from '@/types/api';

/**
 * 裂变第二步 / 查看变更：嵌入共用 ProductEditor。
 * 保留原 props 形状，避免抽屉调用方改动。
 */
export const FissionProductStep = forwardRef<
  ProductEditorHandle,
  {
    productId?: number;
    readOnly?: boolean;
    initialDetail?: DhProductDetailPublic;
    changedKeys?: string[];
    changedAttrList?: DhProductSelectedAttrPublic[];
  }
>(function FissionProductStep(
  {
    productId,
    readOnly = false,
    initialDetail,
    changedKeys = [],
    changedAttrList = [],
  },
  ref,
) {
  return (
    <ProductEditor
      ref={ref}
      embedded
      productId={productId}
      readOnly={readOnly}
      initialDetail={initialDetail}
      changedKeys={changedKeys}
      changedAttrList={changedAttrList}
    />
  );
});
