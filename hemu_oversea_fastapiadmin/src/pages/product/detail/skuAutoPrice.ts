import { fetchDhSkuListPrice } from '@/services/admin/products';
import type { DhProductSkuPublic } from '@/types/api';
import {
  collectDistinctSkuSpecModels,
  extractSkuSpecModel,
  REF_PRICING_CATE_ID,
} from './CommissionRateHint';

export type AutoSkuRetailPriceResult = {
  next: DhProductSkuPublic[];
  /** 写入了预计收入的 SKU 条数 */
  updatedCount: number;
  /** 获取标价失败的型号数 */
  failedCount: number;
  /** 能识别出规格型号的去重数量；为 0 表示没有发起计价 */
  modelCount: number;
};

/**
 * 按规格卡片「自动设置」同一套规则计算 SKU 预计收入。
 * 佣金类目固定为参考定价类目（美容仪），与当前所选产品分类无关；店铺折扣随 storeId。
 */
export async function applyAutoSkuRetailPrices(
  skuList: DhProductSkuPublic[] | null | undefined,
  params: { supplierId: number; storeId: number },
): Promise<AutoSkuRetailPriceResult> {
  const list = skuList || [];
  const models = collectDistinctSkuSpecModels(list);
  if (models.length === 0) {
    return {
      next: list,
      updatedCount: 0,
      failedCount: 0,
      modelCount: 0,
    };
  }

  const priceByModel = new Map<string, number>();
  let failedCount = 0;
  await Promise.all(
    models.map(async (item) => {
      try {
        const data = await fetchDhSkuListPrice(
          {
            supplier_id: params.supplierId,
            sku_code: item.sampleSkuCode,
            store_id: params.storeId,
            cate_id: REF_PRICING_CATE_ID,
          },
          { skipErrorHandler: true },
        );
        const price = Number(data.list_price);
        if (Number.isFinite(price)) {
          priceByModel.set(item.model, Number(price.toFixed(2)));
        } else {
          failedCount += 1;
        }
      } catch {
        failedCount += 1;
      }
    }),
  );

  if (priceByModel.size === 0) {
    return {
      next: list,
      updatedCount: 0,
      failedCount,
      modelCount: models.length,
    };
  }

  let updatedCount = 0;
  const next = list.map((sku) => {
    const model = extractSkuSpecModel(sku.sku_code);
    const price = model ? priceByModel.get(model) : undefined;
    if (price == null) {
      return sku;
    }
    updatedCount += 1;
    return { ...sku, retail_price: price };
  });
  return {
    next,
    updatedCount,
    failedCount,
    modelCount: models.length,
  };
}
