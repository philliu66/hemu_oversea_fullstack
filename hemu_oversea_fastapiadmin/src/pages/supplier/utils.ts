export const SUPPLIER_LIST_PATH = '/supplier/list';
export const SUPPLIER_CREATE_PATH = '/supplier/create';

export function supplierDetailPath(id: number) {
  return `/supplier/detail/${id}`;
}

export function supplierEditPath(id: number) {
  return `/supplier/edit/${id}`;
}

export function parseSupplierId(value?: string) {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

export function confirmPasswordValidator(
  getFieldValue: (name: string) => unknown,
  field = 'adminPassword',
) {
  return (_: unknown, value?: string) => {
    if (!value || getFieldValue(field) === value) {
      return Promise.resolve();
    }
    return Promise.reject(new Error('两次输入的密码不一致'));
  };
}
