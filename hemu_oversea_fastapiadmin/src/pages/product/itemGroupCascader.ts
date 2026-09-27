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

/** 按完整路径从 options 解析展示名；任一节对不上或没有真实名称则返回空串（绝不回退成 ID）。 */
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
      return '';
    }
    const hit = level.find((item) => item.value === value);
    if (!hit) {
      return '';
    }
    const label = String(hit.label ?? '').trim();
    // groupDisplayName 在无中英文名时会回退成 group_id，这种展示要避免
    if (!label || label === value) {
      return '';
    }
    labels.push(label);
    level = hit.children;
  }
  return labels.join(' / ');
}
