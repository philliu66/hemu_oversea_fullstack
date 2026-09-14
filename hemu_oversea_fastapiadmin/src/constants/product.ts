/** 敦煌商品状态编码（与后端 / dh.item.get state 对齐） */
export const DH_PRODUCT_STATES = [
  '100000',
  '100100',
  '100200',
  '100300',
  '100400',
  '100500',
  '100600',
  '100700',
] as const;

export type DhProductStateCode = (typeof DH_PRODUCT_STATES)[number];

export const DH_PRODUCT_STATE_LABEL: Record<DhProductStateCode, string> = {
  '100000': '未定义',
  '100100': '上架产品',
  '100200': '待审核产品',
  '100300': '审核未通过产品',
  '100400': '下架产品',
  '100500': '品牌商投诉产品',
  '100600': '疑似侵权产品',
  '100700': '内容违规品',
};
