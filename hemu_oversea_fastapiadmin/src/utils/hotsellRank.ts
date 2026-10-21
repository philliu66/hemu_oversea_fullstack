/** 解析热卖榜接口回传（与扩展 parse-rank 对齐） */

export type HotsellRankSummary = {
  currentCategory: string;
  itemCount: number;
};

export function parseHotsellRankResponse(
  data: unknown,
): HotsellRankSummary | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }
  const root = data as Record<string, unknown>;
  const category =
    typeof root.currentCategory === 'string' && root.currentCategory.trim()
      ? root.currentCategory.trim()
      : '';

  const pageInfo = root.pageInfoOfProductRank;
  let itemCount = 0;
  if (pageInfo && typeof pageInfo === 'object' && !Array.isArray(pageInfo)) {
    const result = (pageInfo as Record<string, unknown>).result;
    if (Array.isArray(result)) {
      itemCount = result.length;
    }
  }

  if (!category && itemCount === 0) {
    return null;
  }

  return {
    currentCategory: category || '未知',
    itemCount,
  };
}
