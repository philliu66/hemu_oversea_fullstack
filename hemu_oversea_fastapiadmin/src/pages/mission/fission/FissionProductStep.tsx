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
    /** 切换分类时套用 SKU 属性模板（手动添加第二步） */
    applySkuAttrTemplateOnCategoryChange?: boolean;
    /** 产品标题清空并以种子标题为 placeholder（手动添加第二步） */
    seedTitleAsItemNamePlaceholder?: boolean;
    supplierId?: number;
  }
>(function FissionProductStep(
  {
    productId,
    readOnly = false,
    initialDetail,
    changedKeys = [],
    changedAttrList = [],
    applySkuAttrTemplateOnCategoryChange = false,
    seedTitleAsItemNamePlaceholder = false,
    supplierId,
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
      applySkuAttrTemplateOnCategoryChange={
        applySkuAttrTemplateOnCategoryChange
      }
      seedTitleAsItemNamePlaceholder={seedTitleAsItemNamePlaceholder}
      supplierId={supplierId}
    />
  );
});
