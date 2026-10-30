import { Column } from '@ant-design/charts';
import { useModel } from '@umijs/max';
import {
  Button,
  DatePicker,
  Drawer,
  Empty,
  Select,
  Space,
  Spin,
  Tooltip,
  Typography,
  message,
} from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import SupplierSelectField from '@/components/SupplierSelectField';
import { APP_TIMEZONE } from '@/constants/datetime';
import {
  fetchLoginActivitySummary,
  fetchLoginActivityTimeline,
  fetchLoginActivityUsers,
} from '@/services/admin/logs';
import type {
  LoginActivitySpan,
  LoginActivitySummary,
  LoginActivityUserOption,
  LoginLogPublic,
} from '@/types/api';
import { formatDateTime, setupDayjs } from '@/utils/datetime';
import { isPlatformRole } from '@/utils/portalScope';

setupDayjs();

const { RangePicker } = DatePicker;
const { Text } = Typography;

type ActivityRange = [Dayjs, Dayjs];

type LoginActivityDrawerProps = {
  open: boolean;
  seedToken: number;
  record: LoginLogPublic | null;
  onClose: () => void;
};

function defaultRange(): ActivityRange {
  const end = dayjs().tz(APP_TIMEZONE).endOf('day');
  return [end.subtract(6, 'day').startOf('day'), end];
}

function presetRange(days: number): ActivityRange {
  const end = dayjs().tz(APP_TIMEZONE).endOf('day');
  return [end.subtract(days - 1, 'day').startOf('day'), end];
}

function userLabel(nickname: string | null | undefined, username: string) {
  return nickname ? `${nickname}（${username}）` : username;
}

function DayTrack({
  date,
  spans,
}: {
  date: string;
  spans: LoginActivitySpan[];
}) {
  const dayStart = dayjs.tz(date, APP_TIMEZONE).startOf('day');
  const ticks = [0, 6, 12, 18, 24];
  return (
    <div>
      <div
        style={{
          position: 'relative',
          height: 36,
          borderRadius: 6,
          background: 'rgba(0, 0, 0, 0.04)',
          overflow: 'hidden',
        }}
      >
        {spans.map((span) => {
          const start = dayjs.utc(span.start).tz(APP_TIMEZONE);
          const end = dayjs.utc(span.end).tz(APP_TIMEZONE);
          const startMin = Math.max(0, start.diff(dayStart, 'minute', true));
          const endMin = Math.min(24 * 60, end.diff(dayStart, 'minute', true));
          if (endMin <= startMin) {
            return null;
          }
          const left = (startMin / (24 * 60)) * 100;
          const width = Math.max(((endMin - startMin) / (24 * 60)) * 100, 0.6);
          return (
            <Tooltip
              key={`${span.start}-${span.end}`}
              title={`${formatDateTime(span.start)} - ${formatDateTime(span.end)}，${span.active_minutes} 分钟`}
            >
              <div
                style={{
                  position: 'absolute',
                  left: `${left}%`,
                  width: `${width}%`,
                  top: 6,
                  bottom: 6,
                  borderRadius: 4,
                  background: '#1677ff',
                }}
              />
            </Tooltip>
          );
        })}
      </div>
      <div style={{ position: 'relative', height: 22, marginTop: 4 }}>
        {ticks.map((hour) => (
          <span
            key={hour}
            style={{
              position: 'absolute',
              left: `${(hour / 24) * 100}%`,
              transform:
                hour === 0
                  ? undefined
                  : hour === 24
                    ? 'translateX(-100%)'
                    : 'translateX(-50%)',
              fontSize: 12,
              color: 'rgba(0, 0, 0, 0.45)',
            }}
          >
            {String(hour).padStart(2, '0')}:00
          </span>
        ))}
      </div>
    </div>
  );
}

const LoginActivityDrawer: React.FC<LoginActivityDrawerProps> = ({
  open,
  seedToken,
  record,
  onClose,
}) => {
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser;
  const role = currentUser?.access || currentUser?.role;
  const platform = isPlatformRole(role);

  const [supplierId, setSupplierId] = useState<number>();
  const [userId, setUserId] = useState<number>();
  const [users, setUsers] = useState<LoginActivityUserOption[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [range, setRange] = useState<ActivityRange>(defaultRange);
  const [summary, setSummary] = useState<LoginActivitySummary>();
  const [spans, setSpans] = useState<LoginActivitySpan[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>();
  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);

  const runQuery = async (
    next: { userId?: number; supplierId?: number; range: ActivityRange },
    options?: { silent?: boolean },
  ) => {
    if (!next.userId || (platform && !next.supplierId)) {
      if (!options?.silent) {
        message.warning(
          platform && !next.supplierId ? '请先选择供应商和用户' : '请选择用户',
        );
      }
      return;
    }
    const [start, end] = next.range;
    if (!end.isAfter(start)) {
      message.warning('结束时间必须晚于开始时间');
      return;
    }
    if (end.diff(start, 'minute', true) > 31 * 24 * 60) {
      message.warning('最多查询 31 天');
      return;
    }
    const current = ++requestId.current;
    setLoading(true);
    try {
      const payload = {
        user_id: next.userId,
        supplier_id: platform ? next.supplierId : undefined,
        time_from: start.toISOString(),
        time_to: end.toISOString(),
      };
      const [summaryData, timelineData] = await Promise.all([
        fetchLoginActivitySummary(payload),
        fetchLoginActivityTimeline(payload),
      ]);
      if (current !== requestId.current) {
        return;
      }
      setSummary(summaryData);
      setSpans(timelineData.spans);
      setSelectedDate(undefined);
    } catch {
      if (current === requestId.current) {
        setSummary(undefined);
        setSpans([]);
        setSelectedDate(undefined);
      }
    } finally {
      if (current === requestId.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    if (!open || !record || !seedToken) {
      return;
    }
    const nextSupplier = record.supplier_id ?? undefined;
    const nextUser = record.user_id ?? undefined;
    const nextRange = defaultRange();
    setSupplierId(nextSupplier);
    setUserId(nextUser);
    setRange(nextRange);
    setSummary(undefined);
    setSpans([]);
    setSelectedDate(undefined);
    void runQuery(
      { userId: nextUser, supplierId: nextSupplier, range: nextRange },
      { silent: true },
    );
  }, [open, seedToken]);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (platform && !supplierId) {
      setUsers([]);
      return;
    }
    let cancelled = false;
    setUsersLoading(true);
    fetchLoginActivityUsers(platform ? supplierId : undefined)
      .then((items) => {
        if (!cancelled) {
          setUsers(items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUsers([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setUsersLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, platform, supplierId]);

  const userOptions = useMemo(() => {
    const options = users.map((item) => ({
      value: item.id,
      label: userLabel(item.nickname, item.username),
    }));
    if (
      userId &&
      record?.user_id === userId &&
      !options.some((item) => item.value === userId)
    ) {
      options.unshift({
        value: userId,
        label: userLabel(record.nickname, record.username),
      });
    }
    return options;
  }, [users, userId, record]);

  const columnData = useMemo(
    () =>
      (summary?.days ?? []).map((item) => {
        const date = dayjs(item.date).format('YYYY-MM-DD');
        return {
          date,
          day: dayjs(date).format('MM-DD'),
          active_minutes: item.active_minutes,
        };
      }),
    [summary],
  );
  const columnDataRef = useRef(columnData);
  columnDataRef.current = columnData;

  const selectedDay = useMemo(() => {
    if (!selectedDate) {
      return undefined;
    }
    const day = (summary?.days ?? []).find(
      (item) => dayjs(item.date).format('YYYY-MM-DD') === selectedDate,
    );
    if (!day) {
      return undefined;
    }
    const dayStart = dayjs.tz(selectedDate, APP_TIMEZONE).startOf('day');
    const dayEnd = dayStart.add(1, 'day');
    const daySpans = spans.filter((span) => {
      const start = dayjs.utc(span.start).tz(APP_TIMEZONE);
      const end = dayjs.utc(span.end).tz(APP_TIMEZONE);
      return end.isAfter(dayStart) && start.isBefore(dayEnd);
    });
    return { date: selectedDate, active_minutes: day.active_minutes, spans: daySpans };
  }, [selectedDate, summary, spans]);

  return (
    <Drawer
      title="活跃情况"
      open={open}
      width={760}
      destroyOnHidden
      maskClosable={false}
      onClose={onClose}
    >
      <Space wrap style={{ marginBottom: 16 }}>
        {platform ? (
          <SupplierSelectField
            value={supplierId}
            style={{ width: 220 }}
            onChange={(value) => {
              setSupplierId(value);
              setUserId(undefined);
              setSummary(undefined);
              setSpans([]);
              setSelectedDate(undefined);
            }}
          />
        ) : null}
        <Select
          showSearch
          optionFilterProp="label"
          placeholder="请选择用户"
          style={{ width: 240 }}
          loading={usersLoading}
          disabled={platform && !supplierId}
          options={userOptions}
          value={userId}
          onChange={(value) => setUserId(value)}
        />
        <RangePicker
          allowClear={false}
          showTime={{ format: 'HH:mm' }}
          format="YYYY-MM-DD HH:mm"
          value={range}
          presets={[
            { label: '当天', value: presetRange(1) },
            { label: '近3天', value: presetRange(3) },
            { label: '近7天', value: presetRange(7) },
            { label: '近30天', value: presetRange(30) },
          ]}
          onChange={(values) => {
            if (!values?.[0] || !values[1]) {
              return;
            }
            setRange([values[0], values[1]]);
          }}
        />
        <Button
          type="primary"
          loading={loading}
          onClick={() => {
            void runQuery({ userId, supplierId, range });
          }}
        >
          查询
        </Button>
      </Space>

      {!summary && !loading ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            platform && !supplierId
              ? '请先选择供应商和用户'
              : !userId
                ? '请选择用户'
                : '选择时间后查询活跃情况'
          }
        />
      ) : (
        <Spin spinning={loading}>
          <Text type="secondary">
            {summary
              ? `${summary.nickname || summary.username} 合计活跃 ${summary.total_minutes} 分钟`
              : ' '}
          </Text>
          {summary ? (
            <Column
              data={columnData}
              xField="day"
              yField="active_minutes"
              height={260}
              style={{
                maxWidth: 36,
                cursor: 'pointer',
                fill: (datum: { date?: string }) =>
                  datum.date === selectedDate ? '#0958d9' : '#1677ff',
              }}
              axis={{ y: { title: '分钟' } }}
              tooltip={{
                items: [{ field: 'active_minutes', name: '活跃分钟' }],
              }}
              onReady={(chart) => {
                const selectDay = (event: {
                  data?: {
                    data?:
                      | { date?: string; day?: string }
                      | Array<{ date?: string; day?: string }>;
                  };
                }) => {
                  const raw = event?.data?.data;
                  const datum = Array.isArray(raw) ? raw[0] : raw;
                  if (!datum) {
                    return;
                  }
                  const date =
                    datum.date ||
                    columnDataRef.current.find((item) => item.day === datum.day)
                      ?.date;
                  if (date) {
                    setSelectedDate(date);
                  }
                };
                chart.on('click', selectDay);
              }}
            />
          ) : null}
          <div style={{ marginTop: 16 }}>
            {selectedDay ? (
              <>
                <Text>
                  {dayjs.tz(selectedDay.date, APP_TIMEZONE).format('M月D日')}
                  活跃时段（{selectedDay.active_minutes} 分钟）
                </Text>
                <div style={{ marginTop: 12 }}>
                  {selectedDay.spans.length > 0 ? (
                    <DayTrack date={selectedDay.date} spans={selectedDay.spans} />
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="这一天没有活跃记录"
                    />
                  )}
                </div>
              </>
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="点击上方某一天的柱状图，查看当天 0–24 点活跃时段"
              />
            )}
          </div>
        </Spin>
      )}
    </Drawer>
  );
};

export default LoginActivityDrawer;
