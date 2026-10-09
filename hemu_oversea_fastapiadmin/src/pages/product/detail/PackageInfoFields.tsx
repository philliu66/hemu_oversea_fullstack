import { ProFormDependency } from '@ant-design/pro-components';
import { Checkbox, Form, InputNumber, Space, Typography } from 'antd';
import React from 'react';
import type { DhItemWeightRangePublic } from '@/types/api';

function toNumber(value: string | number | null | undefined): number | null {
  if (value == null || value === '') {
    return null;
  }
  const num = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(num) ? num : null;
}

function hasWeightRange(range?: DhItemWeightRangePublic | null): boolean {
  if (!range) {
    return false;
  }
  return (
    range.base_qt != null ||
    range.step_qt != null ||
    range.step_weight != null
  );
}

type PackageInfoFieldsProps = {
  disabled?: boolean;
};

/**
 * 包装信息：字段直连 Form；体积/阶梯用 ProFormDependency 局部订阅。
 */
const PackageInfoFields: React.FC<PackageInfoFieldsProps> = ({
  disabled = false,
}) => {
  const form = Form.useFormInstance();

  const labelStyle: React.CSSProperties = {
    width: 110,
    flex: '0 0 110px',
    lineHeight: '32px',
    textAlign: 'right',
    paddingRight: 8,
    color: 'rgba(0,0,0,0.88)',
  };

  return (
    <div style={{ maxWidth: 900 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          marginBottom: 16,
          flexWrap: 'wrap',
          rowGap: 8,
        }}
      >
        <div style={labelStyle}>
          <Typography.Text type="danger">*</Typography.Text>
          {'包装后重量'}
          :
        </div>
        <Space wrap size={8} align="center" style={{ flex: 1, minWidth: 0 }}>
          <Form.Item name="gross_weight" noStyle>
            <InputNumber min={0} step={0.01} disabled={disabled} style={{ width: 120 }} />
          </Form.Item>
          <Typography.Text type="secondary">{'(公斤/件/个)'}</Typography.Text>
          <ProFormDependency name={['item_weight_range']}>
            {({ item_weight_range }) => {
              const ladderEnabled = hasWeightRange(item_weight_range);
              return (
                <Checkbox
                  disabled={disabled}
                  checked={ladderEnabled}
                  onChange={(event) => {
                    if (event.target.checked) {
                      form.setFieldsValue({
                        item_weight_range: {
                          base_qt: item_weight_range?.base_qt ?? 0,
                          step_qt: item_weight_range?.step_qt ?? 0,
                          step_weight: item_weight_range?.step_weight ?? null,
                        },
                      });
                    } else {
                      form.setFieldsValue({ item_weight_range: null });
                    }
                  }}
                >
                  {'产品计重阶梯设定'}
                </Checkbox>
              );
            }}
          </ProFormDependency>
        </Space>
      </div>

      <ProFormDependency name={['item_weight_range']}>
        {({ item_weight_range }) => {
          if (!hasWeightRange(item_weight_range)) {
            return null;
          }
          const patchRange = (patch: Partial<DhItemWeightRangePublic>) => {
            if (disabled) {
              return;
            }
            form.setFieldsValue({
              item_weight_range: {
                base_qt: item_weight_range?.base_qt ?? null,
                step_qt: item_weight_range?.step_qt ?? null,
                step_weight: item_weight_range?.step_weight ?? null,
                ...patch,
              },
            });
          };
          return (
            <div style={{ marginBottom: 16, paddingLeft: 118 }}>
              <div style={{ marginBottom: 10 }}>
                <Space wrap size={6} align="center">
                  <span>{'买家购买'}</span>
                  <InputNumber
                    min={0}
                    precision={0}
                    disabled={disabled}
                    value={toNumber(item_weight_range?.base_qt) ?? undefined}
                    style={{ width: 88 }}
                    onChange={(value) =>
                      patchRange({
                        base_qt: typeof value === 'number' ? value : null,
                      })
                    }
                  />
                  <span>{'件/个以内，按单位产品重量计算运费。'}</span>
                </Space>
              </div>
              <div>
                <Space wrap size={6} align="center">
                  <span>{'在此基础上，买家每多买'}</span>
                  <InputNumber
                    min={0}
                    precision={0}
                    disabled={disabled}
                    value={toNumber(item_weight_range?.step_qt) ?? undefined}
                    style={{ width: 88 }}
                    onChange={(value) =>
                      patchRange({
                        step_qt: typeof value === 'number' ? value : null,
                      })
                    }
                  />
                  <span>{'件/个，重量增加'}</span>
                  <InputNumber
                    min={0}
                    step={0.01}
                    disabled={disabled}
                    value={toNumber(item_weight_range?.step_weight) ?? undefined}
                    style={{ width: 88 }}
                    onChange={(value) =>
                      patchRange({
                        step_weight: typeof value === 'number' ? value : null,
                      })
                    }
                  />
                  <span>{'公斤。'}</span>
                </Space>
              </div>
            </div>
          );
        }}
      </ProFormDependency>

      <div style={{ display: 'flex', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={labelStyle}>
          <Typography.Text type="danger">*</Typography.Text>
          {'包装后尺寸'}
          :
        </div>
        <ProFormDependency name={['length', 'width', 'height']}>
          {({ length, width, height }) => {
            const volume = (() => {
              const l = toNumber(length);
              const w = toNumber(width);
              const h = toNumber(height);
              if (l == null || w == null || h == null) {
                return null;
              }
              const result = l * w * h;
              return Number.isFinite(result) ? result : null;
            })();
            return (
              <Space wrap size={6} align="center" style={{ flex: 1, minWidth: 0 }}>
                <Form.Item name="length" noStyle>
                  <InputNumber min={0} step={0.1} disabled={disabled} style={{ width: 88 }} />
                </Form.Item>
                <span>X</span>
                <Form.Item name="width" noStyle>
                  <InputNumber min={0} step={0.1} disabled={disabled} style={{ width: 88 }} />
                </Form.Item>
                <span>X</span>
                <Form.Item name="height" noStyle>
                  <InputNumber min={0} step={0.1} disabled={disabled} style={{ width: 88 }} />
                </Form.Item>
                <Typography.Text type="secondary">
                  {'(单位: 厘米, 每件/个'}{' '}
                  <Typography.Text type="danger">
                    {volume == null ? '-' : volume}
                  </Typography.Text>{' '}
                  cm³)
                </Typography.Text>
              </Space>
            );
          }}
        </ProFormDependency>
      </div>
    </div>
  );
};

export default PackageInfoFields;
