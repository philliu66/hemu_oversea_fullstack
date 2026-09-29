import { request } from '@umijs/max';
import type { ApiResponse, PageData } from '@/types/api';

export type PermissionTreeNode = {
  id: number;
  code: string;
  title: string;
  type: string;
  scope: string;
  path?: string | null;
  children?: PermissionTreeNode[];
};

export type RolePublic = {
  id: number;
  supplier_id: number | null;
  name: string;
  remark: string | null;
  is_active: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  permission_codes: string[];
};

function isPlatformIdentity(role?: string) {
  return (
    role === 'platform_admin' ||
    role === 'super_admin' ||
    role === 'platform_staff'
  );
}

export function rolesApiPrefix(portalRole?: string) {
  return isPlatformIdentity(portalRole)
    ? '/api/v1/admin/platform-roles'
    : '/api/v1/admin/supplier-roles';
}

export function staffApiPrefix(portalRole?: string) {
  return isPlatformIdentity(portalRole)
    ? '/api/v1/admin/platform-staff'
    : '/api/v1/admin/supplier-staff';
}

export async function fetchSupplierAssignablePermissionTree() {
  const res = await request<ApiResponse<PermissionTreeNode[]>>(
    '/api/v1/admin/permissions/supplier-assignable-tree',
    { method: 'POST', data: {} },
  );
  return res.data ?? [];
}

export async function fetchRolePermissionTree(portalRole?: string) {
  const res = await request<ApiResponse<PermissionTreeNode[]>>(
    `${rolesApiPrefix(portalRole)}/permission-tree`,
    { method: 'POST', data: {} },
  );
  return res.data ?? [];
}

export async function fetchRoleOptions(portalRole?: string) {
  const res = await request<ApiResponse<{ id: number; name: string }[]>>(
    `${rolesApiPrefix(portalRole)}/options`,
    { method: 'POST', data: {} },
  );
  return res.data ?? [];
}

export async function listRoles(
  portalRole: string | undefined,
  body: { keyword?: string; page?: number; page_size?: number },
) {
  const res = await request<ApiResponse<PageData<RolePublic>>>(
    `${rolesApiPrefix(portalRole)}/list`,
    { method: 'POST', data: body },
  );
  return res.data!;
}

export async function createRole(
  portalRole: string | undefined,
  body: { name: string; remark?: string; permission_codes: string[] },
) {
  const res = await request<ApiResponse<RolePublic>>(
    `${rolesApiPrefix(portalRole)}/create`,
    { method: 'POST', data: body },
  );
  return res.data!;
}

export async function updateRole(
  portalRole: string | undefined,
  body: {
    id: number;
    name?: string;
    remark?: string;
    is_active?: boolean;
    permission_codes?: string[];
  },
) {
  const res = await request<ApiResponse<RolePublic>>(
    `${rolesApiPrefix(portalRole)}/update`,
    { method: 'POST', data: body },
  );
  return res.data!;
}

export async function deleteRole(portalRole: string | undefined, id: number) {
  await request(`${rolesApiPrefix(portalRole)}/delete`, {
    method: 'POST',
    data: { id },
  });
}

export function flattenPermissionTree(
  nodes: PermissionTreeNode[],
): {
  title: string;
  value: string;
  key: string;
  children?: ReturnType<typeof flattenPermissionTree>;
}[] {
  return nodes.map((n) => ({
    title: `${n.title} (${n.code})`,
    value: n.code,
    key: n.code,
    children: n.children?.length
      ? flattenPermissionTree(n.children)
      : undefined,
  }));
}
