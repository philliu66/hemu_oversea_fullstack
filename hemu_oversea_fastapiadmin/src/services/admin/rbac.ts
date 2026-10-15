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
  return role === 'platform_admin' || role === 'platform_staff';
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

export type PermissionButtonOption = {
  code: string;
  title: string;
};

export type MenuPermissionTreeNode = {
  title: string;
  key: string;
  children?: MenuPermissionTreeNode[];
};

/** 把权限树拆成：仅菜单的树 + 各菜单下的按钮列表 */
export function splitMenuAndButtonPermissions(nodes: PermissionTreeNode[]): {
  menuTree: MenuPermissionTreeNode[];
  buttonsByMenuCode: Record<string, PermissionButtonOption[]>;
  rootButtons: PermissionButtonOption[];
  allMenuCodes: Set<string>;
  allButtonCodes: Set<string>;
} {
  const buttonsByMenuCode: Record<string, PermissionButtonOption[]> = {};
  const allMenuCodes = new Set<string>();
  const allButtonCodes = new Set<string>();

  const toButton = (n: PermissionTreeNode): PermissionButtonOption => {
    allButtonCodes.add(n.code);
    return { code: n.code, title: n.title };
  };

  const walkMenus = (
    list: PermissionTreeNode[],
  ): MenuPermissionTreeNode[] => {
    const result: MenuPermissionTreeNode[] = [];
    for (const node of list) {
      if (node.type === 'button') {
        continue;
      }
      allMenuCodes.add(node.code);
      const children = node.children ?? [];
      const buttonChildren = children.filter((c) => c.type === 'button');
      const menuChildren = children.filter((c) => c.type !== 'button');
      if (buttonChildren.length) {
        buttonsByMenuCode[node.code] = buttonChildren.map(toButton);
      }
      result.push({
        title: node.title,
        key: node.code,
        children: menuChildren.length ? walkMenus(menuChildren) : undefined,
      });
    }
    return result;
  };

  const rootButtons = nodes
    .filter((n) => n.type === 'button')
    .map(toButton);

  return {
    menuTree: walkMenus(nodes),
    buttonsByMenuCode,
    rootButtons,
    allMenuCodes,
    allButtonCodes,
  };
}
