import {
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useIntl } from '@umijs/max';
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

type SpecSelfDefDraft = DhProductSpecSelfDefPublic & { key: string };

type SpecAttrsFieldsProps = {
  /** 类目属性定义中，与价格相关的规格属性 */
  priceCategoryAttrs: DhCategoryAttrPublic[];
  /** 商品已选价格属性（is_price_attr=1） */
  priceSelectedAttrs?: DhProductSelectedAttrPublic[];
  /** 自定义规格 */
  specSelfDefs?: DhProductSpecSelfDefPublic[];
  storeId?: number;
  disabled?: boolean;
  onSpecSelfDefsChange?: (next: DhProductSpecSelfDefPublic[]) => void;
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
  }));
}

function toPublicList(drafts: SpecSelfDefDraft[]): DhProductSpecSelfDefPublic[] {
  return drafts.map(({ key: _key, ...rest }) => rest);
}

function SpecSelectedImageTable({
  attr,
  storeId,
  disabled = false,
  onValuePicChange,
}: {
  attr: DhProductSelectedAttrPublic;
  storeId?: number;
  disabled?: boolean;
  onValuePicChange?: (
    attrId: string,
    attrValId: string,
    picUrl: string | null,
  ) => void;
}) {
  const intl = useIntl();
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
        maxWidth: 720,
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
            }}
          >
            {intl.formatMessage({
              id: 'pages.product.detail.specAttrs.customPic',
              defaultMessage: '自定义图片（无图可忽略）',
            })}
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
                }}
              >
                {valueTitle(item)}
              </td>
              <td
                style={{
                  border: '1px solid #d9d9d9',
                  padding: '8px 10px',
                  verticalAlign: 'middle',
                }}
              >
                <DhgateAttrPicUpload
                  storeId={storeId}
                  value={item.pic_url}
                  disabled={disabled}
                  onChange={(picUrl) =>
                    onValuePicChange?.(attr.attr_id, String(valId), picUrl)
                  }
                />
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
  const intl = useIntl();
  const { message } = App.useApp();
  const [drafts, setDrafts] = useState<SpecSelfDefDraft[]>(() =>
    toDrafts(specs),
  );
  const [addValue, setAddValue] = useState('');
  const [editingKey, setEditingKey] = useState<string>();
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    setDrafts((prev) => {
      const prevPublic = JSON.stringify(toPublicList(prev));
      const nextPublic = JSON.stringify(specs || []);
      if (prevPublic === nextPublic) {
        return prev;
      }
      setEditingKey(undefined);
      setEditingName('');
      return toDrafts(specs);
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
        intl.formatMessage({
          id: 'pages.product.detail.specAttrs.nameRequired',
          defaultMessage: '请输入规格名称',
        }),
      );
      return;
    }
    if (
      drafts.some(
        (item) => (item.attr_val_name || '').trim().toLowerCase() === name.toLowerCase(),
      )
    ) {
      message.warning(
        intl.formatMessage({
          id: 'pages.product.detail.specAttrs.nameDuplicate',
          defaultMessage: '规格名称已存在',
        }),
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
        intl.formatMessage({
          id: 'pages.product.detail.specAttrs.nameRequired',
          defaultMessage: '请输入规格名称',
        }),
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
        intl.formatMessage({
          id: 'pages.product.detail.specAttrs.nameDuplicate',
          defaultMessage: '规格名称已存在',
        }),
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
          {intl.formatMessage({
            id: 'pages.product.detail.specAttrs.customSpec',
            defaultMessage: '自定义规格',
          })}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          {drafts.length ? (
            <Space wrap size={[8, 8]}>
              {drafts.map((item) => {
                const isEditing = editingKey === item.key;
                return (
                  <span
                    key={item.key}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '2px 8px',
                      border: '1px solid #d9d9d9',
                      borderRadius: 4,
                      background: '#fafafa',
                    }}
                  >
                    <Checkbox
                      checked
                      disabled={disabled}
                      onChange={(event) => {
                        if (!event.target.checked) {
                          handleDelete(item.key);
                        }
                      }}
                    />
                    {isEditing ? (
                      <Input
                        size="small"
                        value={editingName}
                        disabled={disabled}
                        onChange={(event) => setEditingName(event.target.value)}
                        onPressEnter={() => confirmEdit(item.key)}
                        style={{ width: 140 }}
                      />
                    ) : (
                      <span>{item.attr_val_name || item.attr_val_id || '-'}</span>
                    )}
                    {!disabled && isEditing ? (
                      <>
                        <CheckOutlined
                          style={{ color: '#1677ff', cursor: 'pointer' }}
                          onClick={() => confirmEdit(item.key)}
                        />
                        <CloseOutlined
                          style={{ color: 'rgba(0,0,0,0.45)', cursor: 'pointer' }}
                          onClick={cancelEdit}
                        />
                      </>
                    ) : null}
                    {!disabled && !isEditing ? (
                      <>
                        <EditOutlined
                          style={{ color: 'rgba(0,0,0,0.45)', cursor: 'pointer' }}
                          title={intl.formatMessage({
                            id: 'pages.product.detail.specAttrs.edit',
                            defaultMessage: '编辑',
                          })}
                          onClick={() => startEdit(item)}
                        />
                        <DeleteOutlined
                          style={{ color: 'rgba(0,0,0,0.45)', cursor: 'pointer' }}
                          title={intl.formatMessage({
                            id: 'pages.product.detail.specAttrs.delete',
                            defaultMessage: '删除',
                          })}
                          onClick={() => handleDelete(item.key)}
                        />
                      </>
                    ) : null}
                  </span>
                );
              })}
            </Space>
          ) : (
            <Typography.Text type="secondary">
              {intl.formatMessage({
                id: 'pages.product.detail.specSelfDef.empty',
                defaultMessage: '暂无自定义规格',
              })}
            </Typography.Text>
          )}
          {!disabled ? (
            <div style={{ marginTop: 8 }}>
              <Space.Compact style={{ maxWidth: 360, width: '100%' }}>
                <Input
                  value={addValue}
                  onChange={(event) => setAddValue(event.target.value)}
                  onPressEnter={handleAdd}
                  placeholder={intl.formatMessage({
                    id: 'pages.product.detail.specAttrs.addPlaceholder',
                    defaultMessage: '请输入自定义规格',
                  })}
                />
                <Button type="primary" onClick={handleAdd}>
                  {intl.formatMessage({
                    id: 'pages.product.detail.specAttrs.add',
                    defaultMessage: '添加',
                  })}
                </Button>
              </Space.Compact>
            </div>
          ) : null}
        </div>
      </div>

      {drafts.length ? (
        <table
          style={{
            marginLeft: 100,
            borderCollapse: 'collapse',
            width: '100%',
            maxWidth: 720,
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
                  width: 220,
                }}
              >
                {intl.formatMessage({
                  id: 'pages.product.detail.specAttrs.customSpec',
                  defaultMessage: '自定义规格',
                })}
              </th>
              <th
                style={{
                  border: '1px solid #d9d9d9',
                  background: '#fafafa',
                  padding: '6px 10px',
                  textAlign: 'left',
                  fontWeight: 500,
                }}
              >
                {intl.formatMessage({
                  id: 'pages.product.detail.specAttrs.customPic',
                  defaultMessage: '自定义图片（无图可忽略）',
                })}
              </th>
            </tr>
          </thead>
          <tbody>
            {drafts.map((item) => {
              return (
                <tr key={item.key}>
                  <td
                    style={{
                      border: '1px solid #d9d9d9',
                      padding: 6,
                      verticalAlign: 'middle',
                    }}
                  >
                    <Input
                      value={item.attr_val_name || ''}
                      disabled={disabled}
                      onChange={(event) =>
                        patchDraft(item.key, {
                          attr_val_name: event.target.value,
                        })
                      }
                    />
                  </td>
                  <td
                    style={{
                      border: '1px solid #d9d9d9',
                      padding: '8px 10px',
                      verticalAlign: 'middle',
                    }}
                  >
                    <Space wrap>
                      <DhgateAttrPicUpload
                        storeId={storeId}
                        value={item.pic_url}
                        disabled={disabled}
                        onChange={(picUrl) =>
                          patchDraft(item.key, { pic_url: picUrl })
                        }
                      />
                      {!disabled ? (
                        <Button
                          type="link"
                          size="small"
                          danger
                          onClick={() => handleDelete(item.key)}
                        >
                          {intl.formatMessage({
                            id: 'pages.product.detail.specAttrs.delete',
                            defaultMessage: '删除',
                          })}
                        </Button>
                      ) : null}
                    </Space>
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
  onSpecSelfDefsChange,
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
          storeId={storeId}
          disabled={disabled}
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
