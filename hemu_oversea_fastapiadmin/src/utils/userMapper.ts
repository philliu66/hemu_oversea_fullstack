import type { UserPublic } from '@/types/api';

/** 将后端 UserPublic 映射为 Pro 全局 currentUser */
export function mapUserToCurrentUser(user: UserPublic): API.CurrentUser {
  return {
    name: user.nickname || user.username,
    avatar: user.avatar_url || undefined,
    userid: String(user.id),
    email: user.email,
    phone: user.phone || undefined,
    access: user.role,
    username: user.username,
    nickname: user.nickname,
    role: user.role,
    org_type: user.org_type,
    supplier_id: user.supplier_id ?? undefined,
    is_active: user.is_active,
    permission_codes: user.permission_codes ?? [],
  };
}
