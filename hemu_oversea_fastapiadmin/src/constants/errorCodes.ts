/** 与 FastAPI app.core.errors.ErrorCode 对齐 */
export const ApiErrorCode = {
  SUCCESS: 0,
  BAD_REQUEST: 40000,
  UNAUTHORIZED: 40100,
  FORBIDDEN: 40300,
  NOT_FOUND: 40400,
  CONFLICT: 40900,
  TOO_MANY: 42900,
  VALIDATION: 42200,
  INTERNAL: 50000,
} as const;

export type ApiErrorCode = (typeof ApiErrorCode)[keyof typeof ApiErrorCode];

/** 未登录 / 登录过期：需清理 token 并跳转登录页 */
export function isUnauthorizedCode(code?: number) {
  return code === ApiErrorCode.UNAUTHORIZED;
}
