import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import {
  Alert,
  App,
  Button,
  Card,
  Drawer,
  Input,
  InputNumber,
  Radio,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { createStyles } from 'antd-style';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import SupplierSelectField from '@/components/SupplierSelectField';
import {
  deleteSupplierInspectionSchedule,
  fetchSupplierInspectionSchedule,
  saveSupplierInspectionSchedule,
} from '@/services/admin/suppliers';
import {
  fetchStoreInspectionDispute,
  fetchStoreInspectionPunish,
  fetchStoreList,
} from '@/services/admin/stores';
import type {
  StoreInspectionDisputePublic,
  StoreInspectionPunishPublic,
  StorePublic,
} from '@/types/api';
import {
  needsSupplierSelection,
  resolveRequestSupplierId,
} from '@/utils/portalScope';

const useStyles = createStyles(({ token, css }) => ({
  /** 高风险行：Typography danger / colorError，无红底 */
  disputeDangerRow: css`
    color: ${token.colorError};
    td {
      color: inherit !important;
    }
  `,
}));

const ALL_STORE_VALUE = 'all';
const DAY_PRESET_3 = 3;
const DAY_PRESET_7 = 7;
const DAY_PRESET_10 = 10;
const CUSTOM_DAY_MIN = 1;
const CUSTOM_DAY_MAX = 365;

type DayPreset = '3' | '7' | '10' | 'custom';
type ScheduleDayPreset = 3 | 7 | 10;
type InspectionTabKey = 'punish' | 'dispute';

const SCHEDULE_DAY_OPTIONS = [
  { label: '3 天内', value: 3 },
  { label: '7 天内', value: 7 },
  { label: '10 天内', value: 10 },
];

type InspectionRow = Record<string, unknown> & {
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

function getRecordList(
  data: StoreInspectionPunishPublic | StoreInspectionDisputePublic,
): Record<string, unknown>[] {
  const raw = data.list ?? data.items ?? [];
  return raw.filter(
    (item): item is Record<string, unknown> =>
      !!item && typeof item === 'object' && !Array.isArray(item),
  );
}

function buildPunishRows(data: StoreInspectionPunishPublic): InspectionRow[] {
  return getRecordList(data).map((item, index) => {
    const storeId = pickField(item, ['store_id', 'storeId']);
    const punishId = pickField(item, ['punishId', 'punish_id', 'id']);
    const keyParts = [storeId, punishId].filter(
      (part) => part !== undefined && part !== null && part !== '',
    );
    return {
      ...item,
      _rowKey: keyParts.length > 0 ? keyParts.join('-') : `punish-${index}`,
    };
  });
}

function buildDisputeRows(
  data: StoreInspectionDisputePublic,
): InspectionRow[] {
  return getRecordList(data).map((item, index) => {
    const storeId = pickField(item, ['store_id', 'storeId']);
    const orderNo = pickField(item, ['orderNo', 'order_no', 'rfxNo']);
    const keyParts = [storeId, orderNo].filter(
      (part) => part !== undefined && part !== null && part !== '',
    );
    return {
      ...item,
      _rowKey: keyParts.length > 0 ? keyParts.join('-') : `dispute-${index}`,
    };
  });
}

const StoreInspection: React.FC = () => {
  const { styles } = useStyles();
  const { message, modal } = App.useApp();
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
  const [disputeLoading, setDisputeLoading] = useState(false);
  const [punishRows, setPunishRows] = useState<InspectionRow[]>([]);
  const [disputeRows, setDisputeRows] = useState<InspectionRow[]>([]);
  const [activeTab, setActiveTab] = useState<InspectionTabKey>('punish');
  const [dateRange, setDateRange] = useState<{
    start: string;
    end: string;
  } | null>(null);

  const [scheduleDrawerOpen, setScheduleDrawerOpen] = useState(false);
  const [scheduleDays, setScheduleDays] = useState<ScheduleDayPreset>(7);
  const [scheduleEmails, setScheduleEmails] = useState<string[]>(['']);
  const [scheduleExists, setScheduleExists] = useState(false);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [scheduleDeleting, setScheduleDeleting] = useState(false);

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

  const querying = punishLoading || disputeLoading;

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
        error instanceof Error ? error.message : '加载敦煌店铺失败',
      );
    } finally {
      setStoresLoading(false);
    }
  }, [currentUser, message, supplierId]);

  const clearInspectionResults = useCallback(() => {
    setPunishRows([]);
    setDisputeRows([]);
    setDateRange(null);
  }, []);

  const loadInspection = useCallback(async () => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      message.warning('请先选择供应商');
      return;
    }
    if (!queryDays) {
      message.warning('请输入有效的查询天数（1–365）');
      return;
    }

    const storeId =
      selectedStore === ALL_STORE_VALUE ? undefined : Number(selectedStore);

    setPunishLoading(true);
    setDisputeLoading(true);

    const punishPromise = fetchStoreInspectionPunish({
      supplier_id: supplierId,
      store_id: storeId,
      query_days: queryDays,
    })
      .then((data) => {
        setPunishRows(buildPunishRows(data));
        setDateRange({
          start: data.start_date,
          end: data.end_date,
        });
      })
      .catch((error: unknown) => {
        setPunishRows([]);
        setDateRange(null);
        message.error(
          error instanceof Error ? error.message : '查询处罚信息失败',
        );
      })
      .finally(() => {
        setPunishLoading(false);
      });

    const disputePromise = fetchStoreInspectionDispute({
      supplier_id: supplierId,
      store_id: storeId,
    })
      .then((data) => {
        setDisputeRows(buildDisputeRows(data));
      })
      .catch((error: unknown) => {
        setDisputeRows([]);
        message.error(
          error instanceof Error ? error.message : '查询纠纷订单失败',
        );
      })
      .finally(() => {
        setDisputeLoading(false);
      });

    await Promise.all([punishPromise, disputePromise]);
  }, [currentUser, message, queryDays, selectedStore, supplierId]);

  useEffect(() => {
    void loadStores();
  }, [loadStores]);

  const resetScheduleForm = useCallback(() => {
    setScheduleDays(7);
    setScheduleEmails(['']);
    setScheduleExists(false);
  }, []);

  const loadSchedule = useCallback(async () => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      resetScheduleForm();
      return;
    }
    setScheduleLoading(true);
    try {
      const data = await fetchSupplierInspectionSchedule({
        supplier_id: supplierId,
      });
      if (!data) {
        resetScheduleForm();
        return;
      }
      const days = data.query_days;
      setScheduleDays(
        days === 3 || days === 7 || days === 10 ? days : 7,
      );
      const emails = data.emails
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
      setScheduleEmails(emails.length > 0 ? emails : ['']);
      setScheduleExists(true);
    } catch (error) {
      resetScheduleForm();
      message.error(
        error instanceof Error ? error.message : '加载每日巡检设置失败',
      );
    } finally {
      setScheduleLoading(false);
    }
  }, [currentUser, message, resetScheduleForm, supplierId]);

  useEffect(() => {
    void loadSchedule();
  }, [loadSchedule]);

  const handleSaveSchedule = useCallback(async () => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      message.warning('请先选择供应商');
      return;
    }
    const emails = scheduleEmails.map((item) => item.trim()).filter(Boolean);
    if (emails.length === 0) {
      message.warning('请至少填写一个邮箱地址');
      return;
    }
    setScheduleSaving(true);
    try {
      await saveSupplierInspectionSchedule({
        supplier_id: supplierId,
        query_days: scheduleDays,
        emails: emails.join(','),
      });
      message.success('每日巡检设置已保存');
      setScheduleExists(true);
      await loadSchedule();
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : '保存每日巡检设置失败',
      );
    } finally {
      setScheduleSaving(false);
    }
  }, [
    currentUser,
    loadSchedule,
    message,
    scheduleDays,
    scheduleEmails,
    supplierId,
  ]);

  const handleDeleteSchedule = useCallback(() => {
    if (needsSupplierSelection(currentUser, supplierId) || !supplierId) {
      message.warning('请先选择供应商');
      return;
    }
    if (!scheduleExists) {
      message.warning('当前尚未配置每日巡检');
      return;
    }
    modal.confirm({
      title: '删除每日巡检',
      content:
        '确定删除该供应商的每日巡检设置吗？删除后将不再自动发送巡检邮件。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setScheduleDeleting(true);
        try {
          await deleteSupplierInspectionSchedule({
            supplier_id: supplierId,
          });
          message.success('每日巡检设置已删除');
          resetScheduleForm();
        } catch (error) {
          message.error(
            error instanceof Error ? error.message : '删除每日巡检设置失败',
          );
          throw error;
        } finally {
          setScheduleDeleting(false);
        }
      },
    });
  }, [
    currentUser,
    message,
    modal,
    resetScheduleForm,
    scheduleExists,
    supplierId,
  ]);

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

  const punishColumns: ProColumns<InspectionRow>[] = useMemo(
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

  const isDisputeHighRisk = useCallback((record: InspectionRow) => {
    const flag = pickField(record, [
      'is_high_risk',
      'isWarn',
      'isHighRisk',
      'highRisk',
      'highRiskOrder',
    ]);
    if (typeof flag === 'boolean') {
      return flag;
    }
    if (typeof flag === 'number') {
      return flag === 1;
    }
    const text = String(flag ?? '')
      .trim()
      .toLowerCase();
    return text === '1' || text === 'true' || text === 'y' || text === 'yes';
  }, []);

  const disputeColumns: ProColumns<InspectionRow>[] = useMemo(
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
        title: '订单编号',
        width: 200,
        search: false,
        render: (_, record) => {
          const orderNo = formatCell(
            pickField(record, ['orderNo', 'order_no', 'rfxNo']),
          );
          if (orderNo === '-') {
            return orderNo;
          }
          return (
            <Typography.Text copyable={{ text: orderNo }}>
              {orderNo}
            </Typography.Text>
          );
        },
      },
      {
        title: '订单金额',
        width: 120,
        search: false,
        render: (_, record) =>
          formatCell(
            pickField(record, [
              'orderTotalPrice',
              'orderAmount',
              'actualPrice',
              'order_total_price',
            ]),
          ),
      },
      {
        title: '收货国家',
        width: 120,
        ellipsis: true,
        search: false,
        render: (_, record) =>
          formatCell(
            pickField(record, [
              'country',
              'countryName',
              'countryCn',
              'buyerCountry',
              'receiveCountry',
              'shipToCountry',
            ]),
          ),
      },
      {
        title: '订单状态',
        width: 180,
        search: false,
        onCell: () => ({
          style: { whiteSpace: 'normal', wordBreak: 'break-word' },
        }),
        render: (_, record) =>
          formatCell(
            pickField(record, [
              'orderStatus',
              'orderStatusName',
              'order_status',
            ]),
          ),
      },
      {
        title: '纠纷开启时间',
        width: 170,
        search: false,
        render: (_, record) =>
          formatCell(
            pickField(record, [
              'openTime',
              'disputeOpenDate',
              'disputeOpenTime',
              'dispute_open_date',
            ]),
          ),
      },
    ],
    [],
  );

  return (
    <PageContainer
      title={'店铺巡检'}
      extra={
        <Button
          type="primary"
          onClick={() => {
            setScheduleDrawerOpen(true);
            void loadSchedule();
          }}
        >
          {'每日巡检设置'}
        </Button>
      }
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
                  clearInspectionResults();
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
                  clearInspectionResults();
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
              <Typography.Text type="secondary">{'查询天数'}</Typography.Text>
              <Radio.Group
                options={dayOptions}
                value={dayPreset}
                onChange={(e) => {
                  setDayPreset(e.target.value as DayPreset);
                  clearInspectionResults();
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
                      clearInspectionResults();
                    }}
                  />
                  <Typography.Text type="secondary">{'天'}</Typography.Text>
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
              loading={querying}
              onClick={() => {
                void loadInspection();
              }}
            >
              查询
            </Button>
          </Space>
        </Space>
      </Card>

      <Drawer
        title={'每日巡检设置'}
        open={scheduleDrawerOpen}
        width={480}
        destroyOnHidden
        maskClosable={false}
        onClose={() => setScheduleDrawerOpen(false)}
        styles={{ body: { paddingBottom: 80 } }}
        footer={
          needsSupplierSelection(currentUser, supplierId) ? null : access.canWriteSupplierData ? (
            <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                danger
                loading={scheduleDeleting}
                disabled={!scheduleExists}
                onClick={handleDeleteSchedule}
              >
                {'删除巡检'}
              </Button>
              <Button
                type="primary"
                loading={scheduleSaving}
                onClick={() => {
                  void handleSaveSchedule();
                }}
              >
                {'保存巡检'}
              </Button>
            </Space>
          ) : (
            <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button onClick={() => setScheduleDrawerOpen(false)}>
                {'关闭'}
              </Button>
            </Space>
          )
        }
      >
        {needsSupplierSelection(currentUser, supplierId) ? (
          <Alert
            type="info"
            showIcon
            title={'请先选择供应商后再配置每日巡检'}
          />
        ) : (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Typography.Text
                type="secondary"
                style={{ display: 'block', marginBottom: 8 }}
              >
                {'巡检天数'}
              </Typography.Text>
              <Radio.Group
                options={SCHEDULE_DAY_OPTIONS}
                value={scheduleDays}
                disabled={!access.canWriteSupplierData || scheduleLoading}
                onChange={(e) =>
                  setScheduleDays(e.target.value as ScheduleDayPreset)
                }
                style={{
                  display: 'inline-flex',
                  flexWrap: 'wrap',
                  gap: '8px 16px',
                }}
              />
            </div>
            <div>
              <Typography.Text
                type="secondary"
                style={{ display: 'block', marginBottom: 8 }}
              >
                {'接收邮箱'}
              </Typography.Text>
              <Space
                orientation="vertical"
                size="small"
                style={{ width: '100%' }}
              >
                {scheduleEmails.map((email, index) => (
                  <Space.Compact key={index} style={{ width: '100%' }}>
                    <Input
                      value={email}
                      placeholder={'请输入邮箱地址'}
                      disabled={!access.canWriteSupplierData || scheduleLoading}
                      onChange={(e) => {
                        const next = [...scheduleEmails];
                        next[index] = e.target.value;
                        setScheduleEmails(next);
                      }}
                      style={{ width: '100%' }}
                    />
                    {access.canWriteSupplierData && scheduleEmails.length > 1 ? (
                      <Button
                        icon={<MinusCircleOutlined />}
                        onClick={() => {
                          setScheduleEmails(
                            scheduleEmails.filter((_, i) => i !== index),
                          );
                        }}
                      />
                    ) : null}
                  </Space.Compact>
                ))}
                {access.canWriteSupplierData ? (
                  <Button
                    type="dashed"
                    block
                    icon={<PlusOutlined />}
                    disabled={scheduleLoading}
                    onClick={() => setScheduleEmails([...scheduleEmails, ''])}
                  >
                    {'添加邮箱'}
                  </Button>
                ) : null}
              </Space>
            </div>
            {!access.canWriteSupplierData ? (
              <Typography.Text type="secondary">
                {scheduleExists
                  ? '平台账号仅可查看每日巡检设置'
                  : '当前供应商尚未配置每日巡检'}
              </Typography.Text>
            ) : null}
          </Space>
        )}
      </Drawer>

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as InspectionTabKey)}
          items={[
            {
              key: 'punish',
              label: `处罚信息（${punishRows.length}）`,
              children: (
                <ProTable<InspectionRow>
                  rowKey="_rowKey"
                  columns={punishColumns}
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
              ),
            },
            {
              key: 'dispute',
              label: `纠纷订单（${disputeRows.length}）`,
              children: (
                <ProTable<InspectionRow>
                  rowKey="_rowKey"
                  columns={disputeColumns}
                  dataSource={disputeRows}
                  loading={disputeLoading}
                  search={false}
                  options={false}
                  pagination={{
                    defaultPageSize: 20,
                    showSizeChanger: true,
                  }}
                  toolBarRender={false}
                  rowClassName={(record) =>
                    isDisputeHighRisk(record)
                      ? styles.disputeDangerRow
                      : undefined
                  }
                  locale={{
                    emptyText: '暂无纠纷订单',
                  }}
                />
              ),
            },
          ]}
        />
      </Card>
    </PageContainer>
  );
};

export default StoreInspection;
