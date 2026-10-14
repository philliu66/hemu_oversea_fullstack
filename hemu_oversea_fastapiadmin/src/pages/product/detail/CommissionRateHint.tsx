import { InfoCircleOutlined } from '@ant-design/icons';
import {
  Card,
  Descriptions,
  Popover,
  Progress,
  Skeleton,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import React, { useMemo, useState } from 'react';
import { fetchDhSkuBaseInfo } from '@/services/common/utils';
import type {
  DhCommissionRatePublic,
  DhCommissionUnitPublic,
  DhProductSkuPublic,
  DhSkuBaseInfoPublic,
  StoreBaseDiscountPublic,
} from '@/types/api';

/** 参考定价类目暂定固定查询的类目 ID */
export const REF_PRICING_CATE_ID = '000000';

/**
 * SKU 规格型号：字母+数字，可选紧跟 -数字；其后特殊字符/HTML 实体等截断。
 * 仅用于前端展示去重（定价参考 SKU 型号标签）；查表清洗仍由后端统一处理。
 * 例：MK241&#039; → MK241；TN101-1 → TN101-1；XQ992^ → XQ992
 */
const SKU_SPEC_MODEL_RE = /^[A-Za-z]+[0-9]+(?:-[0-9]+)?/;

type CommissionRateHintProps = {
  /** 类目全路径展示文案 */
  categoryPath?: string;
  /** 是否已选店铺 */
  hasStore?: boolean;
  /** 当前登录用户所属供应商 ID（查 SKU 基础信息） */
  supplierId?: number | null;
  /** 当前商品 SKU 列表（用于提取规格型号） */
  skuList?: DhProductSkuPublic[];
  /** 起定量 */
  minWholesaleQty?: number | null;
  /** 最小销售单位：按件=1，按包=每包数量 */
  packingQuantity?: number | null;
  /** 计件单位展示名 */
  measureUnitLabel?: string;
  commissionLoading?: boolean;
  commissionData?: DhCommissionRatePublic | null;
  storeDiscountLoading?: boolean;
  storeDiscount?: StoreBaseDiscountPublic | null;
};

/** 从单条 sku_code 清洗出规格型号；无法识别时返回 null */
export function extractSkuSpecModel(
  skuCode: string | null | undefined,
): string | null {
  const text = String(skuCode ?? '').trim();
  if (!text) {
    return null;
  }
  const matched = text.match(SKU_SPEC_MODEL_RE);
  return matched?.[0] || null;
}

/**
 * 属性模板用基型号：先走定价参考同款正则，再去掉尾部 -数字。
 * 例：BD001 / BD001-1 / BD001*' → BD001
 */
export function extractSkuBaseModel(
  skuCode: string | null | undefined,
): string | null {
  const model = extractSkuSpecModel(skuCode);
  if (!model) {
    return null;
  }
  return model.replace(/-\d+$/, '') || null;
}

/** 商品 SKU 列表归类为去重基型号（保持首次出现顺序） */
export function collectDistinctSkuBaseModels(
  skuList: DhProductSkuPublic[] | null | undefined,
): string[] {
  const seen = new Set<string>();
  const models: string[] = [];
  for (const sku of skuList || []) {
    const base = extractSkuBaseModel(sku.sku_code);
    if (!base || seen.has(base)) {
      continue;
    }
    seen.add(base);
    models.push(base);
  }
  return models;
}

export type SkuSpecModelSample = {
  /** 正则清洗后的型号（用于展示与去重） */
  model: string;
  /** 首次出现的原始 sku_code（查询接口原样上送） */
  sampleSkuCode: string;
};

/**
 * 商品全部 SKU 按正则清洗后的型号去重（保持首次出现顺序）。
 * 标签展示 model；调 getskubaseinfo 时上送 sampleSkuCode 原样。
 */
export function collectDistinctSkuSpecModels(
  skuList: DhProductSkuPublic[] | null | undefined,
): SkuSpecModelSample[] {
  const seen = new Set<string>();
  const models: SkuSpecModelSample[] = [];
  for (const sku of skuList || []) {
    const raw = String(sku.sku_code ?? '').trim();
    const model = extractSkuSpecModel(raw);
    if (!model || seen.has(model)) {
      continue;
    }
    seen.add(model);
    models.push({ model, sampleSkuCode: raw });
  }
  return models;
}

/** 区间色块颜色（按阶梯顺序） */
const SEGMENT_COLORS = ['#52c41a', '#1677ff', '#faad14', '#f5222d', '#722ed1'];

function formatBound(value: string | null | undefined): string {
  const text = (value || '').trim();
  if (!text) {
    return '∞';
  }
  return text;
}

/** 小数费率转百分比展示（0.08 → 8%） */
function formatPercent(value: string | number | null | undefined): string {
  const text = String(value ?? '').trim();
  if (!text) {
    return '-';
  }
  if (text.endsWith('%')) {
    return text;
  }
  const num = Number(text);
  if (!Number.isFinite(num)) {
    return text;
  }
  if (Math.abs(num) <= 1) {
    const pct = num * 100;
    const fixed = Number.isInteger(pct)
      ? String(pct)
      : pct.toFixed(2).replace(/\.?0+$/, '');
    return `${fixed}%`;
  }
  return `${text}%`;
}

function sortUnits(units: DhCommissionUnitPublic[]): DhCommissionUnitPublic[] {
  return [...units].sort((a, b) => {
    const leftA = Number(a.left_bound);
    const leftB = Number(b.left_bound);
    if (Number.isFinite(leftA) && Number.isFinite(leftB)) {
      return leftA - leftB;
    }
    return String(a.left_bound || '').localeCompare(String(b.left_bound || ''));
  });
}

/**
 * 成交金额刻度：取各区间左边界；最后一个区间的右侧边界不展示。
 */
function buildAmountTicks(units: DhCommissionUnitPublic[]): string[] {
  return units.map((unit) => formatBound(unit.left_bound));
}

/**
 * Ant Design 分段进度条：
 * - 3 段：success + percent + railColor（官方分段能力）
 * - 2 段：percent + railColor
 * - 1 段：铺满单色
 * 各段等宽，便于后续按数值把指示标滑到对应区间。
 */
function CommissionRateProgressBar({
  units,
}: {
  units: DhCommissionUnitPublic[];
}) {
  const segmentColors = useMemo(
    () =>
      units.map((_, index) => SEGMENT_COLORS[index % SEGMENT_COLORS.length]),
    [units],
  );

  const amountTicks = useMemo(() => buildAmountTicks(units), [units]);
  const segmentCount = units.length;
  const segmentWidth = segmentCount > 0 ? 100 / segmentCount : 100;

  const progressProps = useMemo(() => {
    if (segmentCount <= 0) {
      return { percent: 0 as number };
    }
    if (segmentCount === 1) {
      return {
        percent: 100,
        strokeColor: segmentColors[0],
      };
    }
    if (segmentCount === 2) {
      return {
        percent: segmentWidth,
        strokeColor: segmentColors[0],
        railColor: segmentColors[1],
      };
    }
    // ≥3 段：前两段用 success/percent，第三段起用 rail；多于 3 段时其余区间暂并入末段着色
    return {
      percent: segmentWidth * 2,
      success: {
        percent: segmentWidth,
        strokeColor: segmentColors[0],
      },
      strokeColor: segmentColors[1],
      railColor: segmentColors[2],
    };
  }, [segmentCount, segmentColors, segmentWidth]);

  return (
    <div style={{ flex: 1, minWidth: 220, maxWidth: 520 }}>
      {/* 各区间佣金率 */}
      <div style={{ display: 'flex', marginBottom: 4 }}>
        {units.map((unit, index) => (
          <div
            key={`rate-${unit.left_bound ?? ''}-${unit.right_bound ?? ''}-${index}`}
            style={{
              flex: 1,
              textAlign: 'center',
              color: segmentColors[index],
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            {formatPercent(unit.commission_rate)}
          </div>
        ))}
      </div>

      <div style={{ position: 'relative' }}>
        <Progress
          {...progressProps}
          showInfo={false}
          size={{ height: 10 }}
          strokeLinecap="butt"
        />
      </div>

      {/* 成交金额：只展示各区间左边界，最后一项右侧不展示 */}
      <div style={{ display: 'flex', marginTop: 2 }}>
        {amountTicks.map((tick, index) => (
          <Typography.Text
            key={`amt-${tick}-${index}`}
            type="secondary"
            style={{
              fontSize: 12,
              flex: 1,
              textAlign: 'left',
            }}
          >
            {tick}
          </Typography.Text>
        ))}
      </div>
    </div>
  );
}

function formatUsdPrice(value: string | number | null | undefined): string {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return '-';
  }
  return `$${num.toFixed(2)}`;
}

function formatWeightKg(value: string | number | null | undefined): string {
  const text = String(value ?? '').trim();
  if (!text) {
    return '-';
  }
  const num = Number(text);
  if (!Number.isFinite(num)) {
    return text;
  }
  const fixed = Number.isInteger(num)
    ? String(num)
    : num.toFixed(3).replace(/\.?0+$/, '');
  return `${fixed} kg`;
}

function formatPositiveInt(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
    return '-';
  }
  return String(value);
}

function SkuSpecModelTag({
  model,
  sampleSkuCode,
  supplierId,
}: {
  /** 正则清洗后的型号（展示） */
  model: string;
  /** 原始 sku_code（查询原样上送） */
  sampleSkuCode: string;
  supplierId?: number | null;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState<DhSkuBaseInfoPublic | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canQuery = typeof supplierId === 'number' && supplierId > 0;

  const loadInfo = async () => {
    if (!canQuery) {
      setInfo(null);
      setError('当前账号未绑定供应商，无法查询基础信息');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // 原样上送首次出现的 sku_code，清洗由后端统一处理
      const data = await fetchDhSkuBaseInfo(
        { supplier_id: supplierId, sku_code: sampleSkuCode },
        { skipErrorHandler: true },
      );
      setInfo(data);
    } catch {
      setInfo(null);
      setError('暂无该 SKU 型号的基础信息');
    } finally {
      setLoading(false);
    }
  };

  const content = (
    <div style={{ minWidth: 200 }}>
      {loading ? (
        <Spin size="small" />
      ) : error ? (
        <Typography.Text type="secondary">{error}</Typography.Text>
      ) : info ? (
        <Space direction="vertical" size={2}>
          <Typography.Text>
            {'型号 '}
            <Typography.Text strong>{info.sku_code}</Typography.Text>
          </Typography.Text>
          <Typography.Text type="secondary">
            {'系列 '}
            {info.sku_series || '-'}
          </Typography.Text>
          <Typography.Text>
            {'基础价格 '}
            <Typography.Text strong>
              {formatUsdPrice(info.unit_price)}
            </Typography.Text>
          </Typography.Text>
          <Typography.Text>
            {'物流模板 '}
            <Typography.Text strong>
              {info.shipping_template_name || '-'}
            </Typography.Text>
          </Typography.Text>
          <Typography.Text>
            {'重量 '}
            <Typography.Text strong>
              {formatWeightKg(info.weight_kg)}
            </Typography.Text>
          </Typography.Text>
          <Typography.Text>
            {'打包数 '}
            <Typography.Text strong>
              {formatPositiveInt(info.packing_quantity)}
            </Typography.Text>
          </Typography.Text>
          <Typography.Text>
            {'起订量 '}
            <Typography.Text strong>
              {formatPositiveInt(info.min_wholesale_qty)}
            </Typography.Text>
          </Typography.Text>
        </Space>
      ) : (
        <Typography.Text type="secondary">{'点击图标查看基础信息'}</Typography.Text>
      )}
    </div>
  );

  return (
    <Tag color="processing" style={{ marginInlineEnd: 0 }}>
      <Space size={4}>
        <span>{model}</span>
        <Popover
          trigger="click"
          open={open}
          onOpenChange={(next) => {
            setOpen(next);
            if (next) {
              void loadInfo();
            }
          }}
          content={content}
          title={'SKU 基础信息'}
        >
          <InfoCircleOutlined
            style={{ cursor: 'pointer' }}
            onClick={(event) => {
              event.stopPropagation();
            }}
          />
        </Popover>
      </Space>
    </Tag>
  );
}

function buildSalesUnitDisplay(params: {
  minWholesaleQty?: number | null;
  packingQuantity?: number | null;
  measureUnitLabel?: string;
}): React.ReactNode {
  const unitLabel = (params.measureUnitLabel || '').trim() || '件';
  const moq =
    typeof params.minWholesaleQty === 'number' && params.minWholesaleQty > 0
      ? params.minWholesaleQty
      : null;
  const packQtyRaw =
    typeof params.packingQuantity === 'number' && params.packingQuantity > 0
      ? params.packingQuantity
      : 1;
  const minSaleUnit = packQtyRaw;
  const sellByPack = minSaleUnit > 1;

  if (moq == null) {
    return (
      <Typography.Text type="secondary">
        {'请先填写起定量'}
      </Typography.Text>
    );
  }

  const total = moq * minSaleUnit;

  return (
    <Space size={8} align="baseline" wrap>
      <Typography.Text strong style={{ fontSize: 16 }}>
        {total}
      </Typography.Text>
      <Typography.Text>{unitLabel}</Typography.Text>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {sellByPack
          ? `（起定量 ${moq} 包 × 每包 ${minSaleUnit} ${unitLabel}）`
          : `（起定量 ${moq} × 最小销售单位 1）`}
      </Typography.Text>
    </Space>
  );
}

const CommissionRateHint: React.FC<CommissionRateHintProps> = ({
  categoryPath,
  hasStore = false,
  supplierId,
  skuList,
  minWholesaleQty,
  packingQuantity,
  measureUnitLabel,
  commissionLoading = false,
  commissionData = null,
  storeDiscountLoading = false,
  storeDiscount = null,
}) => {
  const units = useMemo(
    () => sortUnits(commissionData?.unit_list || []),
    [commissionData?.unit_list],
  );

  const salesUnitValue = useMemo(
    () =>
      buildSalesUnitDisplay({
        minWholesaleQty,
        packingQuantity,
        measureUnitLabel,
      }),
    [minWholesaleQty, packingQuantity, measureUnitLabel],
  );

  const skuSpecModels = useMemo(
    () => collectDistinctSkuSpecModels(skuList),
    [skuList],
  );

  const showPanel =
    hasStore || Boolean(categoryPath) || skuSpecModels.length > 0;

  if (!showPanel) {
    return null;
  }

  const storeValue = storeDiscountLoading ? (
    <Skeleton.Input active size="small" style={{ width: 200 }} />
  ) : storeDiscount ? (
    <Space size={8} wrap>
      <Typography.Text strong>{storeDiscount.name}</Typography.Text>
      <Tag color="blue">
        {'基础折扣率'}
        {' '}
        {formatPercent(storeDiscount.base_discount)}
      </Tag>
    </Space>
  ) : (
    <Typography.Text type="secondary">
      {hasStore ? '暂无基础折扣率数据' : '未选择店铺'}
    </Typography.Text>
  );

  const skuModelValue =
    skuSpecModels.length > 0 ? (
      <Space size={[4, 4]} wrap>
        {skuSpecModels.map((item) => (
          <SkuSpecModelTag
            key={item.model}
            model={item.model}
            sampleSkuCode={item.sampleSkuCode}
            supplierId={supplierId}
          />
        ))}
      </Space>
    ) : (
      <Typography.Text type="secondary">{'暂无可识别的 SKU 型号'}</Typography.Text>
    );

  let refPricingValue: React.ReactNode;
  if (commissionLoading) {
    refPricingValue = (
      <Space size={8} align="center" wrap>
        <Typography.Text>{'美容仪'}</Typography.Text>
        <Typography.Text type="secondary">{'（'}</Typography.Text>
        <Skeleton.Input active size="small" style={{ width: 320 }} />
        <Typography.Text type="secondary">{'）'}</Typography.Text>
      </Space>
    );
  } else if (units.length === 0) {
    refPricingValue = (
      <Typography.Text>
        {'美容仪'}
        <Typography.Text type="secondary">
          {'（暂无佣金比例数据）'}
        </Typography.Text>
      </Typography.Text>
    );
  } else {
    refPricingValue = (
      <Space align="start" size={4} wrap style={{ width: '100%' }}>
        <Typography.Text style={{ lineHeight: '22px' }}>{'美容仪'}</Typography.Text>
        <Typography.Text type="secondary" style={{ lineHeight: '22px' }}>
          {'（'}
        </Typography.Text>
        <CommissionRateProgressBar units={units} />
        <Typography.Text type="secondary" style={{ lineHeight: '22px' }}>
          {'）'}
        </Typography.Text>
      </Space>
    );
  }

  return (
    <Card size="small" style={{ marginBottom: 16 }} title={'定价参考'}>
      <Descriptions
        size="small"
        column={1}
        labelStyle={{ width: 110, color: 'rgba(0,0,0,0.45)' }}
        contentStyle={{ minWidth: 0 }}
      >
        <Descriptions.Item label={'当前店铺'}>{storeValue}</Descriptions.Item>
        <Descriptions.Item label={'SKU 型号'}>
          {skuModelValue}
        </Descriptions.Item>
        <Descriptions.Item label={'销售单元'}>
          {salesUnitValue}
        </Descriptions.Item>
        <Descriptions.Item label={'佣金参考类目'}>
          {refPricingValue}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};

export default CommissionRateHint;
