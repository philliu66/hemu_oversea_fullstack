export const PRODUCT_LIST_PATH = '/product/list';

export function productDetailPath(id: number) {
  return `/product/detail/${id}`;
}

export function parseProductId(value?: string) {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
}
