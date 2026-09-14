export const STORE_LIST_PATH = '/store/list';
export const STORE_CREATE_PATH = '/store/create';

export function storeDetailPath(id: number) {
  return `/store/detail/${id}`;
}

export function storeEditPath(id: number) {
  return `/store/edit/${id}`;
}

export function parseStoreId(value?: string) {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
}
