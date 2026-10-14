import { BorderOutlined, CheckSquareOutlined } from '@ant-design/icons';
import { Button, Empty, Space, Tree } from 'antd';
import type { DataNode } from 'antd/es/tree';
import React, { useMemo } from 'react';
import {
  splitMenuAndButtonPermissions,
  type MenuPermissionTreeNode,
  type PermissionButtonOption,
  type PermissionTreeNode,
} from '@/services/admin/rbac';

type PermissionCodePickerProps = {
  tree: PermissionTreeNode[];
  value?: string[];
  onChange?: (codes: string[]) => void;
  disabled?: boolean;
  maxHeight?: number | string;
};

function collectDescendantMenuCodes(
  menuTree: MenuPermissionTreeNode[],
  rootCode: string,
): string[] {
  const result: string[] = [];
  const walk = (nodes: MenuPermissionTreeNode[], collecting: boolean) => {
    for (const node of nodes) {
      const next = collecting || node.key === rootCode;
      if (next && node.key !== rootCode) {
        result.push(node.key);
      }
      if (node.children?.length) {
        walk(node.children, next);
      }
    }
  };
  walk(menuTree, false);
  return result;
}

function stopTreeEvent(e: React.SyntheticEvent) {
  e.stopPropagation();
}

/**
 * 菜单权限用 Tree 勾选；各菜单下的按钮权限以按钮选中态展示在对应节点右侧。
 */
const PermissionCodePicker: React.FC<PermissionCodePickerProps> = ({
  tree,
  value,
  onChange,
  disabled,
  maxHeight = 320,
}) => {
  const split = useMemo(() => splitMenuAndButtonPermissions(tree), [tree]);
  const selected = value ?? [];
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const checkedMenuKeys = useMemo(
    () => selected.filter((code) => split.allMenuCodes.has(code)),
    [selected, split.allMenuCodes],
  );

  const emit = (next: string[]) => {
    onChange?.(Array.from(new Set(next)));
  };

  const toggleButton = (menuCode: string | null, buttonCode: string) => {
    const checked = selectedSet.has(buttonCode);
    if (menuCode) {
      const menuButtons = split.buttonsByMenuCode[menuCode] ?? [];
      const menuButtonSet = new Set(menuButtons.map((b) => b.code));
      let nextButtons = selected.filter((code) => menuButtonSet.has(code));
      if (checked) {
        nextButtons = nextButtons.filter((code) => code !== buttonCode);
      } else {
        nextButtons = [...nextButtons, buttonCode];
      }
      const kept = selected.filter((code) => !menuButtonSet.has(code));
      const withMenu =
        nextButtons.length > 0 && !kept.includes(menuCode)
          ? [...kept, menuCode]
          : kept;
      emit([...withMenu, ...nextButtons]);
      return;
    }
    if (checked) {
      emit(selected.filter((code) => code !== buttonCode));
      return;
    }
    emit([...selected, buttonCode]);
  };

  const handleMenuCheck = (
    checked:
      | React.Key[]
      | { checked: React.Key[]; halfChecked: React.Key[] },
  ) => {
    const keys = (
      Array.isArray(checked) ? checked : checked.checked
    ).map(String);
    const uncheckedMenus = checkedMenuKeys.filter(
      (code) => !keys.includes(code),
    );

    let nextButtons = selected.filter((code) =>
      split.allButtonCodes.has(code),
    );
    for (const menuCode of uncheckedMenus) {
      const remove = new Set<string>();
      for (const btn of split.buttonsByMenuCode[menuCode] ?? []) {
        remove.add(btn.code);
      }
      for (const childMenu of collectDescendantMenuCodes(
        split.menuTree,
        menuCode,
      )) {
        for (const btn of split.buttonsByMenuCode[childMenu] ?? []) {
          remove.add(btn.code);
        }
      }
      nextButtons = nextButtons.filter((code) => !remove.has(code));
    }
    emit([...keys, ...nextButtons]);
  };

  const renderButtonGroup = (
    menuCode: string | null,
    buttons: PermissionButtonOption[],
  ) => {
    if (!buttons.length) {
      return null;
    }
    return (
      <span onClick={stopTreeEvent} onMouseDown={stopTreeEvent}>
        <Space size={4} wrap style={{ justifyContent: 'flex-end' }}>
          {buttons.map((b) => {
            const active = selectedSet.has(b.code);
            return (
              <Button
                key={b.code}
                size="small"
                type={active ? 'primary' : 'default'}
                ghost={active}
                disabled={disabled}
                icon={
                  active ? <CheckSquareOutlined /> : <BorderOutlined />
                }
                onClick={() => toggleButton(menuCode, b.code)}
              >
                {b.title}
              </Button>
            );
          })}
        </Space>
      </span>
    );
  };

  const buildTreeData = (nodes: MenuPermissionTreeNode[]): DataNode[] =>
    nodes.map((node) => {
      const buttons = split.buttonsByMenuCode[node.key] ?? [];
      return {
        key: node.key,
        children: node.children?.length
          ? buildTreeData(node.children)
          : undefined,
        title: (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 16,
              width: '100%',
              minHeight: 28,
            }}
          >
            <span style={{ flex: '0 1 auto' }}>{node.title}</span>
            {renderButtonGroup(node.key, buttons)}
          </div>
        ),
      };
    });

  const treeData = buildTreeData(split.menuTree);

  if (!split.menuTree.length && !split.rootButtons.length) {
    return (
      <div
        style={{
          border: '1px solid #f0f0f0',
          borderRadius: 6,
          padding: 8,
        }}
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={'暂无权限'}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        maxHeight,
        overflow: 'auto',
        border: '1px solid #f0f0f0',
        borderRadius: 6,
        padding: 8,
      }}
    >
      {split.rootButtons.length ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            marginBottom: 8,
            padding: '0 4px',
          }}
        >
          <span style={{ color: 'rgba(0,0,0,0.45)' }}>{'其他按钮'}</span>
          {renderButtonGroup(null, split.rootButtons)}
        </div>
      ) : null}
      {split.menuTree.length ? (
        <Tree
          blockNode
          checkable
          disabled={disabled}
          defaultExpandAll
          treeData={treeData}
          checkedKeys={checkedMenuKeys}
          onCheck={handleMenuCheck}
          selectable={false}
        />
      ) : null}
    </div>
  );
};

export default PermissionCodePicker;
