import {
  App,
  Button,
  Checkbox,
  Input,
  Space,
  Typography,
} from 'antd';
import React, { useEffect, useState } from 'react';
import type {
  DhCategoryAttrPublic,
  DhProductSelectedAttrPublic,
  DhProductSelectedAttrValPublic,
  DhProductSpecSelfDefPublic,
} from '@/types/api';
import CategoryAttrsFields from './CategoryAttrsFields';
import DhgateAttrPicUpload from './DhgateAttrPicUpload';
import EditableOptionChip from './EditableOptionChip';

type SpecSelfDefDraft = DhProductSpecSelfDefPublic & {
  key: string;
  /** 是否选中（出现在下方图片表）；取消勾选不删除 */
  selected: boolean;
};

type SpecAttrsFieldsProps = {
  /** 类目属性定义中，与价格相关的规格属性 */
  priceCategoryAttrs: DhCategoryAttrPublic[];
  /** 商品已选价格属性（is_price_attr=1） */
  priceSelectedAttrs?: DhProductSelectedAttrPublic[];
  /** 自定义规格 */
  specSelfDefs?: DhProductSpecSelfDefPublic[];
  storeId?: number;
  disabled?: boolean;
  /** 相对种子有变更的属性 ID，标签与值标红 */
  changedAttrIds?: string[];
  onSpecSelfDefsChange?: (next: DhProductSpecSelfDefPublic[]) => void;
  /** 规格属性勾选/填写变更 */
  onSelectedAttrsChange?: (next: DhProductSelectedAttrPublic[]) => void;
  onValuePicChange?: (
    attrId: string,
    attrValId: string,
    picUrl: string | null,
  ) => void;
};

function attrTitle(attr: DhProductSelectedAttrPublic): string {
  return attr.attr_name_cn?.trim() || attr.attr_name?.trim() || attr.attr_id;
}

function valueTitle(item: DhProductSelectedAttrValPublic): string {
  const en = item.line_attrval_name?.trim() || '';
  const cn = item.line_attrval_name_cn?.trim() || '';
  if (en && cn && en !== cn) {
    return `${en}(${cn})`;
  }
  return en || cn || item.attr_val_id || '-';
}

function toDrafts(list?: DhProductSpecSelfDefPublic[]): SpecSelfDefDraft[] {
  return (list || []).map((item, index) => ({
    key:
      [
        item.attr_val_id,
        item.attr_val_name,
        item.pic_url,
        index,
      ]
        .filter(Boolean)
        .join('|') || `spec-${index}`,
    attr_val_id: item.attr_val_id ?? null,
    spec_attr_name: item.spec_attr_name ?? null,
    attr_val_name: item.attr_val_name ?? null,
    pic_url: item.pic_url ?? null,
    selected: true,
  }));
}

function toPublicList(drafts: SpecSelfDefDraft[]): DhProductSpecSelfDefPublic[] {
  return drafts
    .filter((item) => item.selected)
    .map(({ key: _key, selected: _selected, ...rest }) => rest);
}

function SpecSelectedImageTable({
  attr,
  storeId,
  disabled = false,
  onValuePicChange,
  onDeselectValue,
}: {
  attr: DhProductSelectedAttrPublic;
  storeId?: number;
  disabled?: boolean;
  onValuePicChange?: (
    attrId: string,
    attrValId: string,
    picUrl: string | null,
  ) => void;
  onDeselectValue?: (attrId: string, attrValId: string) => void;
}) {
  const rows = attr.values || [];
  if (!rows.length) {
    return null;
  }
  const hasPicFeature = rows.some((item) => Boolean(item.pic_url));
  if (!hasPicFeature && !onValuePicChange) {
    return null;
  }

  return (
    <table
      style={{
        marginTop: 12,
        marginLeft: 100,
        borderCollapse: 'collapse',
        width: '100%',
        maxWidth: 480,
        fontSize: 13,
      }}
    >
      <thead>
        <tr>
          <th
            style={{
              border: '1px solid #d9d9d9',
              background: '#fafafa',
              padding: '6px 10px',
              textAlign: 'left',
              fontWeight: 500,
              width: 160,
            }}
          >
            {attrTitle(attr)}
          </th>
          <th
            style={{
              border: '1px solid #d9d9d9',
              background: '#fafafa',
              padding: '6px 10px',
              textAlign: 'left',
              fontWeight: 500,
              width: 120,
            }}
          >
            {'自定义图片（无图可忽略）'}
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((item, index) => {
          const valId = item.attr_val_id || `${attr.attr_id}-${index}`;
          return (
            <tr key={valId}>
              <td
                style={{
                  border: '1px solid #d9d9d9',
                  padding: '8px 10px',
                  verticalAlign: 'middle',
                  width: 160,
                }}
              >
                <Space size={8} wrap>
                  <span>{valueTitle(item)}</span>
                  {!disabled && onDeselectValue ? (
                    <Button
                      type="link"
                      size="small"
                      danger
                      style={{ padding: 0, height: 'auto' }}
                      onClick={() =>
                        onDeselectValue(attr.attr_id, String(valId))
                      }
                    >
                      {'删除'}
                    </Button>
                  ) : null}
                </Space>
              </td>
              <td
                style={{
                  border: '1px solid #d9d9d9',
                  padding: '8px 10px',
                  verticalAlign: 'middle',
                  width: 120,
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    display: 'inline-flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <DhgateAttrPicUpload
                    storeId={storeId}
                    value={item.pic_url}
                    disabled={disabled}
                    compact
                    onChange={(picUrl) =>
                      onValuePicChange?.(attr.attr_id, String(valId), picUrl)
                    }
                  />
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function PriceAttrFallback({
  attrs,
  storeId,
  disabled = false,
  onValuePicChange,
}: {
  attrs: DhProductSelectedAttrPublic[];
  storeId?: number;
  disabled?: boolean;
  onValuePicChange?: (
    attrId: string,
    attrValId: string,
    picUrl: string | null,
  ) => void;
}) {
  if (!attrs.length) {
    return null;
  }
  return (
    <div>
      {attrs.map((attr) => (
        <div key={attr.attr_id} style={{ marginBottom: 16 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              columnGap: 12,
            }}
          >
            <div
              style={{
                width: 88,
                flexShrink: 0,
                textAlign: 'left',
                paddingTop: 5,
                color: 'rgba(0,0,0,0.88)',
              }}
            >
              {attrTitle(attr)}
            </div>
            <Space wrap size={[12, 8]} style={{ flex: 1 }}>
              {(attr.values || []).map((item, index) => (
                <Checkbox
                  key={item.attr_val_id || `${attr.attr_id}-${index}`}
                  checked
                >
                  {valueTitle(item)}
                </Checkbox>
              ))}
            </Space>
          </div>
          <SpecSelectedImageTable
            attr={attr}
            storeId={storeId}
            disabled={disabled}
            onValuePicChange={onValuePicChange}
          />
        </div>
      ))}
    </div>
  );
}

function CustomSpecSection({
  specs,
  storeId,
  disabled = false,
  onChange,
}: {
  specs: DhProductSpecSelfDefPublic[];
  storeId?: number;
  disabled?: boolean;
  onChange?: (next: DhProductSpecSelfDefPublic[]) => void;
}) {
  const { message } = App.useApp();
  const [drafts, setDrafts] = useState<SpecSelfDefDraft[]>(() =>
    toDrafts(specs),
  );
  const [addValue, setAddValue] = useState('');
  const [editingKey, setEditingKey] = useState<string>();
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    setDrafts((prev) => {
      const incoming = toDrafts(specs);
      const incomingNames = new Set(
        incoming.map((item) => (item.attr_val_name || '').trim().toLowerCase()),
      );
      // 父级只存已选中的规格；本地未勾选项需合并回来，避免取消勾选被当成删除
      const keptUnselected = prev.filter((item) => {
        if (item.selected) {
          return false;
        }
        const name = (item.attr_val_name || '').trim().toLowerCase();
        return name && !incomingNames.has(name);
      });
      const prevPublic = JSON.stringify(toPublicList(prev));
      const nextPublic = JSON.stringify(specs || []);
      if (prevPublic === nextPublic && keptUnselected.length === 0) {
        return prev;
      }
      if (prevPublic !== nextPublic) {
        setEditingKey(undefined);
        setEditingName('');
      }
      return [...incoming, ...keptUnselected];
    });
  }, [specs]);

  const commit = (next: SpecSelfDefDraft[]) => {
    if (disabled) {
      return;
    }
    setDrafts(next);
    onChange?.(toPublicList(next));
  };

  const handleAdd = () => {
    const name = addValue.trim();
    if (!name) {
      message.warning(
        '请输入规格名称',
      );
      return;
    }
    if (
      drafts.some(
        (item) => (item.attr_val_name || '').trim().toLowerCase() === name.toLowerCase(),
      )
    ) {
      message.warning(
        '规格名称已存在',
      );
      return;
    }
  const next: SpecSelfDefDraft[] = [
      ...drafts,
      {
        key: `spec-new-${Date.now()}`,
        attr_val_id: null,
        spec_attr_name: null,
        attr_val_name: name,
        pic_url: null,
        selected: true,
      },
    ];
    setAddValue('');
    commit(next);
  };

  const handleDelete = (key: string) => {
    commit(drafts.filter((item) => item.key !== key));
    if (editingKey === key) {
      setEditingKey(undefined);
      setEditingName('');
    }
  };

  const startEdit = (item: SpecSelfDefDraft) => {
    setEditingKey(item.key);
    setEditingName(item.attr_val_name || '');
  };

  const cancelEdit = () => {
    setEditingKey(undefined);
    setEditingName('');
  };

  const confirmEdit = (key: string) => {
    const name = editingName.trim();
    if (!name) {
      message.warning(
        '请输入规格名称',
      );
      return;
    }
    if (
      drafts.some(
        (item) =>
          item.key !== key &&
          (item.attr_val_name || '').trim().toLowerCase() === name.toLowerCase(),
      )
    ) {
      message.warning(
        '规格名称已存在',
      );
      return;
    }
    commit(
      drafts.map((item) =>
        item.key === key ? { ...item, attr_val_name: name } : item,
      ),
    );
    cancelEdit();
  };

  const patchDraft = (key: string, patch: Partial<SpecSelfDefDraft>) => {
    commit(
      drafts.map((item) => (item.key === key ? { ...item, ...patch } : item)),
    );
  };

  return (
    <div style={{ marginTop: 8 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          columnGap: 12,
          marginBottom: 12,
        }}
      >
        <div
          style={{
            width: 88,
            flexShrink: 0,
            textAlign: 'left',
            paddingTop: 5,
            color: 'rgba(0,0,0,0.88)',
            lineHeight: '22px',
          }}
        >
          {'自定义规格'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          {drafts.length ? (
            <Space wrap size={[8, 8]}>
              {drafts.map((item) => {
                const isEditing = editingKey === item.key;
                return (
                  <EditableOptionChip
                    key={item.key}
                    label={item.attr_val_name || item.attr_val_id || '-'}
                    checked={item.selected}
                    disabled={disabled}
                    editing={isEditing}
                    editingValue={editingName}
                    onCheckedChange={(checked) => {
                      commit(
                        drafts.map((row) =>
                          row.key === item.key
                            ? { ...row, selected: checked }
                            : row,
                        ),
                      );
                    }}
                    onEditingValueChange={setEditingName}
                    onStartEdit={() => startEdit(item)}
                    onConfirmEdit={() => confirmEdit(item.key)}
                    onCancelEdit={cancelEdit}
                    onDelete={() => handleDelete(item.key)}
                  />
                );
              })}
            </Space>
          ) : (
            <Typography.Text type="secondary">
              {'暂无自定义规格'}
            </Typography.Text>
          )}
          {!disabled ? (
            <div style={{ marginTop: 8 }}>
              <Space.Compact style={{ maxWidth: 360, width: '100%' }}>
                <Input
                  value={addValue}
                  onChange={(event) => setAddValue(event.target.value)}
                  onPressEnter={handleAdd}
                  placeholder={'请输入自定义规格'}
                />
                <Button type="primary" onClick={handleAdd}>
                  {'添加'}
                </Button>
              </Space.Compact>
            </div>
          ) : null}
        </div>
      </div>

      {drafts.some((item) => item.selected) ? (
        <table
          style={{
            marginLeft: 100,
            borderCollapse: 'collapse',
            width: '100%',
            maxWidth: 480,
            fontSize: 13,
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  border: '1px solid #d9d9d9',
                  background: '#fafafa',
                  padding: '6px 10px',
                  textAlign: 'left',
                  fontWeight: 500,
                  width: 160,
                }}
              >
                {'自定义规格'}
              </th>
              <th
                style={{
                  border: '1px solid #d9d9d9',
                  background: '#fafafa',
                  padding: '6px 10px',
                  textAlign: 'left',
                  fontWeight: 500,
                  width: 120,
                }}
              >
                {'自定义图片（无图可忽略）'}
              </th>
            </tr>
          </thead>
          <tbody>
            {drafts
              .filter((item) => item.selected)
              .map((item) => {
              return (
                <tr key={item.key}>
                  <td
                    style={{
                      border: '1px solid #d9d9d9',
                      padding: 6,
                      verticalAlign: 'middle',
                      width: 160,
                    }}
                  >
                    <Space size={8} style={{ width: '100%' }}>
                      <Input
                        value={item.attr_val_name || ''}
                        disabled={disabled}
                        style={{ flex: 1, minWidth: 0 }}
                        onChange={(event) =>
                          patchDraft(item.key, {
                            attr_val_name: event.target.value,
                          })
                        }
                      />
                      {!disabled ? (
                        <Button
                          type="link"
                          size="small"
                          danger
                          style={{ padding: 0, height: 'auto', flexShrink: 0 }}
                          onClick={() =>
                            patchDraft(item.key, { selected: false })
                          }
                        >
                          {'删除'}
                        </Button>
                      ) : null}
                    </Space>
                  </td>
                  <td
                    style={{
                      border: '1px solid #d9d9d9',
                      padding: '8px 10px',
                      verticalAlign: 'middle',
                      width: 120,
                      textAlign: 'center',
                    }}
                  >
                    <div
                      style={{
                        display: 'inline-flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                      }}
                    >
                      <DhgateAttrPicUpload
                        storeId={storeId}
                        value={item.pic_url}
                        disabled={disabled}
                        compact
                        onChange={(picUrl) =>
                          patchDraft(item.key, { pic_url: picUrl })
                        }
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

const SpecAttrsFields: React.FC<SpecAttrsFieldsProps> = ({
  priceCategoryAttrs,
  priceSelectedAttrs,
  specSelfDefs,
  storeId,
  disabled = false,
  changedAttrIds,
  onSpecSelfDefsChange,
  onSelectedAttrsChange,
  onValuePicChange,
}) => {
  const specs = specSelfDefs || [];
  const selected = priceSelectedAttrs || [];
  const definedIds = new Set(
    priceCategoryAttrs.map((item) => String(item.attr_id)),
  );
  const fallbackSelected = selected.filter(
    (item) => !definedIds.has(String(item.attr_id)),
  );

  return (
    <div>
      {priceCategoryAttrs.length > 0 ? (
        <CategoryAttrsFields
          attrs={priceCategoryAttrs}
          selectedAttrs={selected}
          showSelectedPics
          customAddMode
          storeId={storeId}
          disabled={disabled}
          changedAttrIds={changedAttrIds}
          onSelectedAttrsChange={onSelectedAttrsChange}
          onValuePicChange={onValuePicChange}
        />
      ) : null}
      {fallbackSelected.length > 0 ? (
        <PriceAttrFallback
          attrs={fallbackSelected}
          storeId={storeId}
          disabled={disabled}
          onValuePicChange={onValuePicChange}
        />
      ) : null}
      <CustomSpecSection
        specs={specs}
        storeId={storeId}
        disabled={disabled}
        onChange={onSpecSelfDefsChange}
      />
    </div>
  );
};

export default SpecAttrsFields;
