import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import {
  Alert,
  App,
  Button,
  Card,
  InputNumber,
  Radio,
  Space,
  Tag,
  Typography,
} from 'antd';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import SupplierSelectField from '@/components/SupplierSelectField';
import {
  fetchStoreInspectionPunish,
  fetchStoreList,
} from '@/services/admin/stores';
import type { StoreInspectionPunishPublic, StorePublic } from '@/types/api';
import {
  needsSupplierSelection,
  resolveRequestSupplierId,
} from '@/utils/portalScope';

const ALL_STORE_VALUE = 'all';
const DAY_PRESET_3 = 3;
const DAY_PRESET_7 = 7;
const DAY_PRESET_10 = 10;
const CUSTOM_DAY_MIN = 1;
const CUSTOM_DAY_MAX = 365;

type DayPreset = '3' | '7' | '10' | 'custom';

type PunishRow = Record<string, unknown> & {
  _rowKey: string;
};

function pickField(record: Record<string, unknown>, keys: string[]): unknown {
  for (const key of keys) {
    const value = record[key];
    if (value !== undefined && value !== null && value !== '') {
      return value;
    }
  }
  return undefined;
}

function formatCell(value: unknown): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function getPunishList(
  data: StoreInspectionPunishPublic,
): Record<string, unknown>[] {
  const raw = data.list ?? data.items ?? [];
  return raw.filter(
    (item): item is Record<string, unknown> =>
      !!item && typeof item === 'object' && !Array.isArray(item),
  );
}

function buildPunishRows(data: StoreInspectionPunishPublic): PunishRow[] {
  return getPunishList(data).map((item, index) => {
    const storeId = pickField(item, ['store_id', 'storeId']);
    const punishId = pickField(item, ['punishId', 'punish_id', 'id']);
    const keyParts = [storeId, punishId].filter(
      (part) => part !== undefined && part !== null && part !== '',
    );
    return {
      ...item,
      _rowKey: keyParts.length > 0 ? keyParts.join('-') : `row-${index}`,
    };
  });
}

const StoreInspection: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const [selectedSupplierId, setSelectedSupplierId] = useState<number>();
  const supplierId = resolveRequestSupplierId(currentUser, selectedSupplierId);

  const [stores, setStores] = useState<StorePublic[]>([]);
  const [storesLoading, setStoresLoading] = useState(false);
  const [selectedStore, setSelectedStore] = useState<string>(ALL_STORE_VALUE);
  const [dayPreset, setDayPreset] = useState<DayPreset>('7');
  const [customDays, setCustomDays] = useState<number | null>(30);
  const [punishLoading, setPunishLoading] = useState(false);
  const [punishRows, setPunishRows] = useState<PunishRow[]>([]);
  const [dateRange, setDateRange] = useState<{
    start: string;
    end: string;
  } | null>(null);

  const queryDays = useMemo(() => {
    if (dayPreset === '3') {
      return DAY_PRESET_3;
    }
    if (dayPreset === '7') {
      return DAY_PRESET_7;
    }
    if (dayPreset === '10') {
      return DAY_PRESET_10;
    }
    return customDays && customDays >= CUSTOM_DAY_MIN ? customDays : null;
  }, [customDays, dayPreset]);

  const loadStores = useCallback(async () => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      setStores([]);
      return;
    }
    setStoresLoading(true);
    try {
      const data = await fetchStoreList({
        supplier_id: supplierId,
        store_type: 'dhgate',
        page: 1,
        page_size: 100,
      });
      setStores(data.items);
    } catch (error) {
      setStores([]);
      message.error(
        error instanceof Error
          ? error.message
          : '加载敦煌店铺失败',
      );
    } finally {
      setStoresLoading(false);
    }
  }, [currentUser, message, supplierId]);

  const loadPunish = useCallback(async () => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      message.warning('请先选择供应商');
      return;
    }
    if (!queryDays) {
      message.warning(
        '请输入有效的查询天数（1–365）',
      );
      return;
    }
    setPunishLoading(true);
    try {
      const storeId =
        selectedStore === ALL_STORE_VALUE ? undefined : Number(selectedStore);
      const data = await fetchStoreInspectionPunish({
        supplier_id: supplierId,
        store_id: storeId,
        query_days: queryDays,
      });
      setPunishRows(buildPunishRows(data));
      setDateRange({
        start: data.start_date,
        end: data.end_date,
      });
    } catch (error) {
      setPunishRows([]);
      setDateRange(null);
      message.error(
        error instanceof Error
          ? error.message
          : '查询处罚信息失败',
      );
    } finally {
      setPunishLoading(false);
    }
  }, [currentUser, message, queryDays, selectedStore, supplierId]);

  useEffect(() => {
    void loadStores();
  }, [loadStores]);

  const storeOptions = useMemo(
    () => [
      {
        label: '全部',
        value: ALL_STORE_VALUE,
      },
      ...stores.map((store) => ({
        label: store.name,
        value: String(store.id),
      })),
    ],
    [stores],
  );

  const dayOptions = useMemo(
    () => [
      {
        label: '3 天内',
        value: '3',
      },
      {
        label: '7 天内',
        value: '7',
      },
      {
        label: '10 天内',
        value: '10',
      },
      {
        label: '自定义',
        value: 'custom',
      },
    ],
    [],
  );

  const columns: ProColumns<PunishRow>[] = useMemo(
    () => [
      {
        title: '店铺标识',
        width: 160,
        ellipsis: true,
        search: false,
        render: (_, record) =>
          formatCell(
            pickField(record, ['store_identifier', 'storeIdentifier']),
          ),
      },
      {
        title: '处罚编号',
        width: 120,
        search: false,
        render: (_, record) => {
          const punishId = formatCell(
            pickField(record, ['punishId', 'punish_id', 'id']),
          );
          const status = String(
            pickField(record, ['punishStatus', 'status']) ?? '',
          );
          const isActive = status === '1';
          const isReleased = status === '2';
          return (
            <Space orientation="vertical" size={4}>
              <span>{punishId}</span>
              {isActive || isReleased ? (
                <Tag color={isActive ? 'error' : 'success'}>
                  {isActive ? '处罚中' : '已解除'}
                </Tag>
              ) : null}
            </Space>
          );
        },
      },
      {
        title: '处罚类型',
        width: 200,
        ellipsis: true,
        search: false,
        render: (_, record) =>
          formatCell(
            pickField(record, [
              'punishTypeName',
              'punishType',
              'typeName',
              'type',
            ]),
          ),
      },
      {
        title: '处罚原因',
        width: 200,
        ellipsis: true,
        search: false,
        render: (_, record) =>
          formatCell(
            pickField(record, [
              'punishReason',
              'reason',
              'reasonDesc',
              'remark',
            ]),
          ),
      },
      {
        title: '处罚日期',
        width: 140,
        search: false,
        render: (_, record) => formatCell(pickField(record, ['createDateStr'])),
      },
      {
        title: '处罚到期日',
        width: 140,
        search: false,
        render: (_, record) =>
          formatCell(pickField(record, ['punishEndTimeStr'])),
      },
    ],
    [],
  );

  return (
    <PageContainer
      title={'店铺巡检'}
    >
      <Card loading={storesLoading} style={{ marginBottom: 16 }}>
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          {access.canPlatform ? (
            <div>
              <Typography.Text type="secondary" style={{ marginRight: 12 }}>
                {'供应商'}
              </Typography.Text>
              <SupplierSelectField
                value={selectedSupplierId}
                style={{ width: 280 }}
                onChange={(v) => {
                  setSelectedSupplierId(v);
                  setSelectedStore(ALL_STORE_VALUE);
                  setPunishRows([]);
                  setDateRange(null);
                }}
              />
            </div>
          ) : null}
          {needsSupplierSelection(currentUser, supplierId) ? (
            <Alert
              type="info"
              showIcon
              title={'请先选择供应商后再查询店铺巡检信息'}
            />
          ) : (
          <div>
            <Typography.Text type="secondary" style={{ marginRight: 12 }}>
              {'店铺'}
            </Typography.Text>
            <Radio.Group
              options={storeOptions}
              value={selectedStore}
              onChange={(e) => {
                setSelectedStore(String(e.target.value));
                setDateRange(null);
              }}
              style={{
                display: 'inline-flex',
                flexWrap: 'wrap',
                gap: '8px 16px',
              }}
            />
          </div>
          )}
          <Space orientation="vertical" size="small" style={{ width: '100%' }}>
            <Space wrap align="center">
              <Typography.Text type="secondary">
                {'查询天数'}
              </Typography.Text>
              <Radio.Group
                options={dayOptions}
                value={dayPreset}
                onChange={(e) => {
                  setDayPreset(e.target.value as DayPreset);
                  setDateRange(null);
                }}
                style={{
                  display: 'inline-flex',
                  flexWrap: 'wrap',
                  gap: '8px 16px',
                }}
              />
              {dayPreset === 'custom' ? (
                <Space size={4} align="center">
                  <InputNumber
                    min={CUSTOM_DAY_MIN}
                    max={CUSTOM_DAY_MAX}
                    value={customDays}
                    onChange={(value) => {
                      setCustomDays(typeof value === 'number' ? value : null);
                      setDateRange(null);
                    }}
                  />
                  <Typography.Text type="secondary">
                    {'天'}
                  </Typography.Text>
                </Space>
              ) : null}
              {dateRange ? (
                <Typography.Text type="secondary">
                  {`查询区间：${dateRange.start} ~ ${dateRange.end}`}
                </Typography.Text>
              ) : null}
            </Space>
            <Button
              type="primary"
              loading={punishLoading}
              onClick={() => {
                void loadPunish();
              }}
            >
              查询
            </Button>
          </Space>
        </Space>
      </Card>

      <ProTable<PunishRow>
        rowKey="_rowKey"
        columns={columns}
        dataSource={punishRows}
        loading={punishLoading}
        search={false}
        options={false}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
        toolBarRender={false}
        locale={{
          emptyText: '暂无处罚信息',
        }}
      />
    </PageContainer>
  );
};

export default StoreInspection;
