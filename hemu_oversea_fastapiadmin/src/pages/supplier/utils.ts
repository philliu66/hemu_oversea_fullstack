export const SUPPLIER_LIST_PATH = '/supplier/list';

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
