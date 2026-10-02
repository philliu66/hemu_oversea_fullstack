import {
  Card,
  Descriptions,
  Skeleton,
  Space,
  Tag,
  Typography,
} from 'antd';
import React, { useMemo } from 'react';
import type {
  DhCommissionRatePublic,
  DhCommissionUnitPublic,
  StoreBaseDiscountPublic,
} from '@/types/api';

type CommissionRateHintProps = {
  /** 类目全路径展示文案 */
  categoryPath?: string;
  /** 是否已选店铺 */
  hasStore?: boolean;
  /** 是否已选到可查佣金的二级类目 */
  hasCategory?: boolean;
  commissionLoading?: boolean;
  commissionData?: DhCommissionRatePublic | null;
  storeDiscountLoading?: boolean;
  storeDiscount?: StoreBaseDiscountPublic | null;
};

function formatBound(value: string | null | undefined): string {
  const text = (value || '').trim();
  if (!text) {
    return '∞';
  }
  return text;
}

function formatRange(unit: DhCommissionUnitPublic): string {
  const leftBracket = unit.left_bound_close === false ? '(' : '[';
  const rightBracket = unit.right_bound_close === false ? ')' : ']';
  return `${leftBracket}${formatBound(unit.left_bound)}, ${formatBound(
    unit.right_bound,
  )}${rightBracket}`;
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

const CommissionRateHint: React.FC<CommissionRateHintProps> = ({
  categoryPath,
  hasStore = false,
  hasCategory = false,
  commissionLoading = false,
  commissionData = null,
  storeDiscountLoading = false,
  storeDiscount = null,
}) => {
  const units = useMemo(
    () => sortUnits(commissionData?.unit_list || []),
    [commissionData?.unit_list],
  );

  const showPanel = hasStore || hasCategory || Boolean(categoryPath);

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

  const categoryValue = categoryPath?.trim() ? (
    <Typography.Text>{categoryPath}</Typography.Text>
  ) : (
    <Typography.Text type="secondary">
      {'未选择类目'}
    </Typography.Text>
  );

  let commissionValue: React.ReactNode;
  if (!hasCategory) {
    commissionValue = (
      <Typography.Text type="secondary">
        {'选择至二级类目后可查看佣金率'}
      </Typography.Text>
    );
  } else if (commissionLoading) {
    commissionValue = (
      <Skeleton.Input active size="small" style={{ width: 280 }} />
    );
  } else if (units.length === 0) {
    commissionValue = (
      <Typography.Text type="warning">
        {'当前类目暂无佣金率数据，请先同步类目佣金率'}
      </Typography.Text>
    );
  } else {
    commissionValue = (
      <Space size={[8, 8]} wrap align="center">
        {units.map((unit, index) => (
          <Tag
            key={`${unit.left_bound ?? ''}-${unit.right_bound ?? ''}-${index}`}
            color="red"
          >
            {formatRange(unit)}
            {' → '}
            <Typography.Text strong style={{ color: 'inherit' }}>
              {formatPercent(unit.commission_rate)}
            </Typography.Text>
          </Tag>
        ))}
        <Typography.Text type="secondary">
          {'（暂定依据美容仪类目计算佣金率）'}
        </Typography.Text>
      </Space>
    );
  }

  return (
    <Card
      size="small"
      style={{ marginBottom: 16 }}
      title={'当前店铺与类目定价参考'}
    >
      <Descriptions
        size="small"
        column={1}
        labelStyle={{ width: 96, color: 'rgba(0,0,0,0.45)' }}
        contentStyle={{ minWidth: 0 }}
      >
        <Descriptions.Item
          label={'当前店铺'}
        >
          {storeValue}
        </Descriptions.Item>
        <Descriptions.Item
          label={'当前类目'}
        >
          {categoryValue}
        </Descriptions.Item>
        <Descriptions.Item
          label={'类目佣金率'}
        >
          {commissionValue}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};

export default CommissionRateHint;
