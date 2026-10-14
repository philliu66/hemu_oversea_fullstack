import { ProFormDependency } from '@ant-design/pro-components';
import { App, Divider, Form, Skeleton } from 'antd';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { fetchStoreBaseDiscount } from '@/services/admin/stores';
import type {
  DhCategoryAttrPublic,
  DhCommissionRatePublic,
  DhProductSelectedAttrPublic,
  DhProductSkuPublic,
  DhProductSpecSelfDefPublic,
  StoreBaseDiscountPublic,
} from '@/types/api';
import CommissionRateHint from './CommissionRateHint';
import PriceRangeFields from './PriceRangeFields';
import {
  mergeManagedAttrsIntoList,
  patchAttrValuePic,
  saleCategoryAttrs,
  selectedAttrsForCategoryIds,
} from './productFormMapping';
import { useMeasureUnits } from './measureUnits';
import { resolveMeasureDisplayName } from './SaleInfoFields';
import SpecAttrsFields from './SpecAttrsFields';
import SpecSkuTable from './SpecSkuTable';
import {
  buildSkuListFromSpecAttrs,
  buildSpecComboSignature,
} from './specSkuBuild';

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
  const { modal } = App.useApp();
  const { options: measureOptions } = useMeasureUnits();
  /** 取消确认时 remount 规格区，回滚本地草稿到表单值 */
  const [specUiEpoch, setSpecUiEpoch] = useState(0);

  const applyPriceAttrsToForm = useCallback(
    (
      priceCategoryAttrs: DhCategoryAttrPublic[],
      nextSelected: DhProductSelectedAttrPublic[],
    ) => {
      const managedIds = priceCategoryAttrs.map((item) => String(item.attr_id));
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
    },
    [form],
  );

  const requestSpecDrivenUpdate = useCallback(
    (options: {
      priceCategoryAttrs: DhCategoryAttrPublic[];
      currentPriceSelected: DhProductSelectedAttrPublic[];
      currentSpecs: DhProductSpecSelfDefPublic[];
      nextPriceSelected?: DhProductSelectedAttrPublic[];
      nextSpecs?: DhProductSpecSelfDefPublic[];
    }) => {
      const nextPrice =
        options.nextPriceSelected ?? options.currentPriceSelected;
      const nextSpecs = options.nextSpecs ?? options.currentSpecs;
      const prevKey = buildSpecComboSignature(
        options.currentPriceSelected,
        options.currentSpecs,
      );
      const nextKey = buildSpecComboSignature(nextPrice, nextSpecs);
      const comboChanged = prevKey !== nextKey;

      const commit = () => {
        if (options.nextPriceSelected) {
          applyPriceAttrsToForm(
            options.priceCategoryAttrs,
            options.nextPriceSelected,
          );
        }
        if (options.nextSpecs) {
          form.setFieldsValue({ item_spec_self_def_list: options.nextSpecs });
        }
        if (comboChanged) {
          form.setFieldsValue({
            sku_list: buildSkuListFromSpecAttrs(nextPrice, nextSpecs),
          });
        }
      };

      if (!comboChanged) {
        commit();
        return;
      }

      const existingSkus = (form.getFieldValue('sku_list') ||
        []) as DhProductSkuPublic[];
      if (existingSkus.length === 0) {
        commit();
        return;
      }

      modal.confirm({
        title: '重新计算 SKU',
        content: '目前已存在的数据将会被清空',
        okText: '确认',
        cancelText: '取消',
        onOk: () => {
          commit();
        },
        onCancel: () => {
          setSpecUiEpoch((value) => value + 1);
        },
      });
    },
    [applyPriceAttrsToForm, form, modal],
  );

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
        // 按类目定义 sale_attr 分流；与商品属性区块统一
        const priceCategoryAttrs = saleCategoryAttrs(categoryAttrs);
        const priceSelectedAttrs = selectedAttrsForCategoryIds(
          attr_list,
          priceCategoryAttrs.map((item) => String(item.attr_id)),
        );
        const currentSpecs = (item_spec_self_def_list ||
          []) as DhProductSpecSelfDefPublic[];
        const measureUnitLabel =
          resolveMeasureDisplayName(measure_id, measureOptions) || '件';

        const handlePriceAttrsChange = (
          nextSelected: DhProductSelectedAttrPublic[],
        ) => {
          requestSpecDrivenUpdate({
            priceCategoryAttrs,
            currentPriceSelected: priceSelectedAttrs,
            currentSpecs,
            nextPriceSelected: nextSelected,
          });
        };

        const handleSpecSelfDefsChange = (
          next: DhProductSpecSelfDefPublic[],
        ) => {
          requestSpecDrivenUpdate({
            priceCategoryAttrs,
            currentPriceSelected: priceSelectedAttrs,
            currentSpecs,
            nextSpecs: next,
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
                    key={specUiEpoch}
                    disabled={readOnly}
                    changedAttrIds={changedCategoryAttrIds}
                    priceCategoryAttrs={priceCategoryAttrs}
                    priceSelectedAttrs={priceSelectedAttrs}
                    specSelfDefs={currentSpecs}
                    storeId={store_id || undefined}
                    onSelectedAttrsChange={
                      readOnly ? undefined : handlePriceAttrsChange
                    }
                    onValuePicChange={
                      readOnly ? undefined : handleAttrValuePicChange
                    }
                    onSpecSelfDefsChange={
                      readOnly ? undefined : handleSpecSelfDefsChange
                    }
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
                    specSelfDefs={currentSpecs}
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
