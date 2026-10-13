import { Form, Select } from 'antd';
import React, { useEffect, useState } from 'react';
import {
  fetchStoreAftersaleTemplates,
  fetchStoreShippingTemplates,
} from '@/services/admin/stores';
import { withCurrentTemplateOption } from './templateSelectUtils';

type TemplateInfoFieldsProps = {
  disabled?: boolean;
  afterSaleLabel?: React.ReactNode;
  shippingLabel?: React.ReactNode;
  afterSaleChanged?: boolean;
  shippingChanged?: boolean;
  changedControlStyle?: React.CSSProperties;
};

type SelectOption = { label: string; value: string };

/**
 * 模板信息：售后 / 物流选项随 store_id 在本组件内加载；
 * 详情回填的 id 在 options 未就绪时用占位项，就绪后重建 Select 以映射名称。
 */
const TemplateInfoFields: React.FC<TemplateInfoFieldsProps> = ({
  disabled = false,
  afterSaleLabel = '售后模板',
  shippingLabel = '物流模板',
  afterSaleChanged = false,
  shippingChanged = false,
  changedControlStyle,
}) => {
  const form = Form.useFormInstance();
  const storeId = Form.useWatch('store_id', form) as number | undefined;
  const afterSaleId = Form.useWatch('after_sale_template_id', form) as
    | string
    | null
    | undefined;
  const shippingId = Form.useWatch('shipping_model_id', form) as
    | string
    | null
    | undefined;

  const [afterSaleOptions, setAfterSaleOptions] = useState<SelectOption[]>([]);
  const [afterSaleLoading, setAfterSaleLoading] = useState(false);
  const [shippingOptions, setShippingOptions] = useState<SelectOption[]>([]);
  const [shippingLoading, setShippingLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!storeId) {
      setAfterSaleOptions([]);
      setAfterSaleLoading(false);
      return;
    }
    setAfterSaleLoading(true);
    void fetchStoreAftersaleTemplates(storeId)
      .then((list) => {
        if (cancelled) {
          return;
        }
        const options = list.map((item) => ({
          label: item.name?.trim() || item.after_sale_template_id,
          value: item.after_sale_template_id,
        }));
        setAfterSaleOptions(
          withCurrentTemplateOption(
            options,
            form.getFieldValue('after_sale_template_id'),
          ),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setAfterSaleOptions(
            withCurrentTemplateOption(
              [],
              form.getFieldValue('after_sale_template_id'),
            ),
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAfterSaleLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [form, storeId]);

  useEffect(() => {
    let cancelled = false;
    if (!storeId) {
      setShippingOptions([]);
      setShippingLoading(false);
      return;
    }
    setShippingLoading(true);
    void fetchStoreShippingTemplates(storeId)
      .then((list) => {
        if (cancelled) {
          return;
        }
        const options = list.map((item) => ({
          label: item.name?.trim() || item.shipping_model_id,
          value: item.shipping_model_id,
        }));
        setShippingOptions(
          withCurrentTemplateOption(
            options,
            form.getFieldValue('shipping_model_id'),
          ),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setShippingOptions(
            withCurrentTemplateOption(
              [],
              form.getFieldValue('shipping_model_id'),
            ),
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setShippingLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [form, storeId]);

  // 详情晚于列表回填时，给当前 id 补占位 option
  useEffect(() => {
    setAfterSaleOptions((prev) => withCurrentTemplateOption(prev, afterSaleId));
  }, [afterSaleId]);

  useEffect(() => {
    setShippingOptions((prev) => withCurrentTemplateOption(prev, shippingId));
  }, [shippingId]);

  const afterSaleKey = afterSaleLoading
    ? 'aftersale-pending'
    : 'aftersale-ready';
  const shippingKey = shippingLoading ? 'shipping-pending' : 'shipping-ready';

  return (
    <>
      <Form.Item name="after_sale_template_id" label={afterSaleLabel}>
        <Select
          key={afterSaleKey}
          disabled={disabled}
          loading={afterSaleLoading}
          showSearch
          allowClear
          placeholder={'请选择售后模板'}
          options={afterSaleOptions}
          optionFilterProp="label"
          style={{
            maxWidth: 360,
            ...(afterSaleChanged ? changedControlStyle : undefined),
          }}
        />
      </Form.Item>
      <Form.Item name="shipping_model_id" label={shippingLabel}>
        <Select
          key={shippingKey}
          disabled={disabled}
          loading={shippingLoading}
          showSearch
          allowClear
          placeholder={'请选择物流模板'}
          options={shippingOptions}
          optionFilterProp="label"
          style={{
            maxWidth: 360,
            ...(shippingChanged ? changedControlStyle : undefined),
          }}
        />
      </Form.Item>
    </>
  );
};

export default TemplateInfoFields;
