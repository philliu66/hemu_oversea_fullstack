import { ProFormDependency } from '@ant-design/pro-components';
import { Divider, Form, Skeleton } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { fetchStoreBaseDiscount } from '@/services/admin/stores';
import type {
  DhCategoryAttrPublic,
  DhCommissionRatePublic,
  DhProductSelectedAttrPublic,
  StoreBaseDiscountPublic,
} from '@/types/api';
import CommissionRateHint from './CommissionRateHint';
import PriceRangeFields from './PriceRangeFields';
import {
  mergeManagedAttrsIntoList,
  patchAttrValuePic,
  priceProductAttrs,
} from './productFormMapping';
import { useMeasureUnits } from './measureUnits';
import { resolveMeasureDisplayName } from './SaleInfoFields';
import SpecAttrsFields from './SpecAttrsFields';
import SpecSkuTable from './SpecSkuTable';

type ProductSpecSkuBlockProps = {
  readOnly?: boolean;
  categoryAttrsLoading?: boolean;
  categoryAttrs: DhCategoryAttrPublic[];
  changedCategoryAttrIds: string[];
  categoryPath?: string;
  supplierId?: number | null;
  itemCode?: string | null;
  commissionLoading?: boolean;
  commissionData?: DhCommissionRatePublic | null;
};

/**
 * 店铺折扣无表单项：挂在 store_id 依赖下按店拉取（声明式 request 语义）。
 */
function StoreDiscountRequest({
  storeId,
  children,
}: {
  storeId?: number;
  children: (ctx: {
    discount: StoreBaseDiscountPublic | null;
    loading: boolean;
  }) => React.ReactNode;
}) {
  const [discount, setDiscount] = useState<StoreBaseDiscountPublic | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const reqRef = useRef(0);

  useEffect(() => {
    if (!storeId) {
      reqRef.current += 1;
      setDiscount(null);
      setLoading(false);
      return;
    }
    const reqId = reqRef.current + 1;
    reqRef.current = reqId;
    setLoading(true);
    setDiscount(null);
    void fetchStoreBaseDiscount(storeId, { skipErrorHandler: true })
      .then((data) => {
        if (reqRef.current === reqId) {
          setDiscount(data);
        }
      })
      .catch(() => {
        if (reqRef.current === reqId) {
          setDiscount(null);
        }
      })
      .finally(() => {
        if (reqRef.current === reqId) {
          setLoading(false);
        }
      });
  }, [storeId]);

  return <>{children({ discount, loading })}</>;
}

/**
 * 规格 / SKU / 佣金提示：ProFormDependency 局部订阅联动字段。
 */
export default function ProductSpecSkuBlock({
  readOnly = false,
  categoryAttrsLoading = false,
  categoryAttrs,
  changedCategoryAttrIds,
  categoryPath,
  supplierId,
  itemCode,
  commissionLoading = false,
  commissionData = null,
}: ProductSpecSkuBlockProps) {
  const form = Form.useFormInstance();
  const { options: measureOptions } = useMeasureUnits();

  return (
    <ProFormDependency
      name={[
        'store_id',
        'attr_list',
        'item_spec_self_def_list',
        'sku_list',
        'measure_id',
        'packing_quantity',
        'min_wholesale_qty',
        'price_config_type',
        'item_wholesale_range_list',
      ]}
    >
      {({
        store_id,
        attr_list,
        item_spec_self_def_list,
        sku_list,
        measure_id,
        packing_quantity,
        min_wholesale_qty,
        price_config_type,
        item_wholesale_range_list,
      }) => {
        const priceSelectedAttrs = priceProductAttrs(attr_list);
        const priceCategoryAttrs = priceSelectedAttrs
          .map((item) =>
            categoryAttrs.find(
              (attr) => String(attr.attr_id) === String(item.attr_id),
            ),
          )
          .filter((item): item is DhCategoryAttrPublic => Boolean(item));
        const measureUnitLabel =
          resolveMeasureDisplayName(measure_id, measureOptions) || '件';

        const handlePriceAttrsChange = (
          nextSelected: DhProductSelectedAttrPublic[],
        ) => {
          const managedIds = priceCategoryAttrs.map((item) =>
            String(item.attr_id),
          );
          const priced = nextSelected.map((item) => ({
            ...item,
            is_price_attr: '1',
          }));
          const prev = form.getFieldValue('attr_list') as
            | DhProductSelectedAttrPublic[]
            | undefined;
          form.setFieldsValue({
            attr_list: mergeManagedAttrsIntoList(prev, managedIds, priced),
          });
        };

        const handleAttrValuePicChange = (
          attrId: string,
          attrValId: string,
          picUrl: string | null,
        ) => {
          const prev = form.getFieldValue('attr_list') as
            | DhProductSelectedAttrPublic[]
            | undefined;
          form.setFieldsValue({
            attr_list: patchAttrValuePic(prev, attrId, attrValId, picUrl),
          });
        };

        return (
          <StoreDiscountRequest storeId={store_id}>
            {({ discount, loading: discountLoading }) => (
              <>
                {categoryAttrsLoading ? (
                  <Skeleton
                    active
                    paragraph={{ rows: 6 }}
                    style={{ marginBottom: 24 }}
                  />
                ) : (
                  <SpecAttrsFields
                    disabled={readOnly}
                    changedAttrIds={changedCategoryAttrIds}
                    priceCategoryAttrs={priceCategoryAttrs}
                    priceSelectedAttrs={priceSelectedAttrs}
                    specSelfDefs={item_spec_self_def_list}
                    storeId={store_id || undefined}
                    onSelectedAttrsChange={
                      readOnly ? undefined : handlePriceAttrsChange
                    }
                    onValuePicChange={
                      readOnly ? undefined : handleAttrValuePicChange
                    }
                    onSpecSelfDefsChange={(next) => {
                      form.setFieldsValue({ item_spec_self_def_list: next });
                    }}
                  />
                )}
                <Divider plain style={{ margin: '28px 0' }}>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>
                    {'商品规格属性生成的规格sku'}
                  </span>
                </Divider>
                <CommissionRateHint
                  categoryPath={categoryPath}
                  hasStore={Boolean(store_id)}
                  supplierId={supplierId}
                  skuList={sku_list}
                  minWholesaleQty={min_wholesale_qty}
                  packingQuantity={packing_quantity}
                  measureUnitLabel={measureUnitLabel}
                  commissionLoading={commissionLoading}
                  commissionData={commissionData}
                  storeDiscountLoading={discountLoading}
                  storeDiscount={discount}
                />
                <Form.Item
                  name="sku_list"
                  noStyle
                  valuePropName="skuList"
                  trigger="onChange"
                >
                  <SpecSkuTable
                    disabled={readOnly || categoryAttrsLoading}
                    priceSelectedAttrs={priceSelectedAttrs}
                    specSelfDefs={item_spec_self_def_list}
                    itemCode={itemCode}
                    measureUnitLabel={measureUnitLabel}
                    supplierId={supplierId}
                    storeId={store_id}
                    commissionUnits={commissionData?.unit_list}
                    storeDiscount={discount}
                  />
                </Form.Item>
                <PriceRangeFields
                  disabled={readOnly}
                  priceConfigType={price_config_type}
                  minWholesaleQty={min_wholesale_qty}
                  ranges={item_wholesale_range_list}
                  measureUnitLabel={measureUnitLabel}
                  onPriceConfigTypeChange={(value) => {
                    form.setFieldsValue({ price_config_type: value });
                  }}
                  onMinWholesaleQtyChange={(value) => {
                    form.setFieldsValue({ min_wholesale_qty: value });
                  }}
                  onRangesChange={(next) => {
                    form.setFieldsValue({ item_wholesale_range_list: next });
                  }}
                />
              </>
            )}
          </StoreDiscountRequest>
        );
      }}
    </ProFormDependency>
  );
}
