import { useIntl } from '@umijs/max';
import { Alert, Skeleton, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import React, { useMemo } from 'react';
import type { DhCommissionRatePublic, DhCommissionUnitPublic } from '@/types/api';

type CommissionRateHintProps = {
  loading?: boolean;
  data?: DhCommissionRatePublic | null;
  /** 当前是否已选类目（无类目时不展示） */
  hasCategory?: boolean;
};

type RateRow = {
  key: string;
  range: string;
  rate: string;
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

function formatRate(value: string | null | undefined): string {
  const text = (value || '').trim();
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
  // 官方多为小数费率（如 0.08 → 8%）
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
  loading = false,
  data,
  hasCategory = false,
}) => {
  const intl = useIntl();

  const rows = useMemo<RateRow[]>(() => {
    const units = sortUnits(data?.unit_list || []);
    return units.map((unit, index) => ({
      key: `${unit.left_bound ?? ''}-${unit.right_bound ?? ''}-${index}`,
      range: formatRange(unit),
      rate: formatRate(unit.commission_rate),
    }));
  }, [data?.unit_list]);

  const columns = useMemo<ColumnsType<RateRow>>(
    () => [
      {
        title: intl.formatMessage({
          id: 'pages.product.detail.commission.col.range',
          defaultMessage: '价格区间（USD）',
        }),
        dataIndex: 'range',
        key: 'range',
        width: '55%',
      },
      {
        title: intl.formatMessage({
          id: 'pages.product.detail.commission.col.rate',
          defaultMessage: '佣金费率',
        }),
        dataIndex: 'rate',
        key: 'rate',
        render: (value: string) => (
          <Typography.Text strong type="danger">
            {value}
          </Typography.Text>
        ),
      },
    ],
    [intl],
  );

  if (!hasCategory) {
    return null;
  }

  if (loading) {
    return (
      <Skeleton
        active
        title={false}
        paragraph={{ rows: 2 }}
        style={{ marginBottom: 16 }}
      />
    );
  }

  if (!data || rows.length === 0) {
    return (
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message={intl.formatMessage({
          id: 'pages.product.detail.commission.empty',
          defaultMessage: '当前类目暂无佣金率数据，请先同步类目佣金率',
        })}
      />
    );
  }

  return (
    <Alert
      type="info"
      showIcon
      style={{ marginBottom: 16 }}
      message={intl.formatMessage({
        id: 'pages.product.detail.commission.title',
        defaultMessage: '当前类目佣金率标准',
      })}
      description={
        <Table<RateRow>
          size="small"
          pagination={false}
          rowKey="key"
          columns={columns}
          dataSource={rows}
          style={{ marginTop: 8, maxWidth: 480 }}
        />
      }
    />
  );
};

export default CommissionRateHint;
