import type { DefaultOptionType } from 'antd/es/cascader';
import type { DhProductGroupPublic } from '@/types/api';

export type ItemGroupCascaderOption = DefaultOptionType & {
  value: string;
  label: string;
  isLeaf?: boolean;
  children?: ItemGroupCascaderOption[];
};

export function groupDisplayName(group: DhProductGroupPublic): string {
  return (group.group_name || group.group_en_name || group.group_id).trim();
}

export function toItemGroupCascaderOption(
  group: DhProductGroupPublic,
): ItemGroupCascaderOption {
  const children = (group.children || [])
    .filter((item) => Boolean(item.group_id))
    .map((item) => toItemGroupCascaderOption(item));
  return {
    value: group.group_id,
    label: groupDisplayName(group),
    isLeaf: children.length === 0,
    children: children.length ? children : undefined,
  };
}

export function toItemGroupCascaderOptions(
  groups: DhProductGroupPublic[],
): ItemGroupCascaderOption[] {
  return groups
    .filter((item) => Boolean(item.group_id))
    .map((item) => toItemGroupCascaderOption(item));
}

export function findItemGroupPath(
  options: ItemGroupCascaderOption[],
  targetId: string,
  path: string[] = [],
): string[] | undefined {
  const target = String(targetId || '').trim();
  if (!target) {
    return undefined;
  }
  for (const option of options) {
    const next = [...path, option.value];
    if (option.value === target) {
      return next;
    }
    if (option.children?.length) {
      const found = findItemGroupPath(option.children, target, next);
      if (found) {
        return found;
      }
    }
  }
  return undefined;
}

/**
 * 分组树里找不到当前 item_group_id 时，补一个叶子选项，避免 Cascader 初始空白。
 * 常见于本地分组尚未完整同步，或平台侧分组已删但商品仍挂着旧 ID。
 */
export function withFallbackGroupOption(
  options: ItemGroupCascaderOption[],
  groupId: string | null | undefined,
): ItemGroupCascaderOption[] {
  const id = String(groupId || '').trim();
  if (!id) {
    return options;
  }
  if (findItemGroupPath(options, id)) {
    return options;
  }
  return [
    ...options,
    {
      value: id,
      label: id,
      isLeaf: true,
    },
  ];
}

/** 按完整路径从 options 解析展示名。 */
export function resolveItemGroupLabels(
  options: ItemGroupCascaderOption[],
  path: string[] | undefined,
): string {
  if (!path?.length) {
    return '';
  }
  const labels: string[] = [];
  let level: ItemGroupCascaderOption[] | undefined = options;
  for (const raw of path) {
    const value = String(raw || '').trim();
    if (!value || !level?.length) {
      return labels.length ? labels.join(' / ') : value;
    }
    const hit = level.find((item) => item.value === value);
    if (!hit) {
      // 树里对不上时，至少把已解析到的名称 + 当前 ID 拼出来，避免整框空白
      return [...labels, value].join(' / ');
    }
    const label = String(hit.label ?? '').trim() || value;
    labels.push(label);
    level = hit.children;
  }
  return labels.join(' / ');
}
