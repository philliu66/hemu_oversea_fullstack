import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { InfoCircleOutlined } from '@ant-design/icons';
import {
  App,
  Button,
  Empty,
  Image,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { Key } from 'react';
import { PAGE_SIZE_DEFAULT } from '@/constants/api';
import {
  asMissionHotsaleDhConfig,
  CONFIG_KEY_MISSION_HOTSALE_DH,
  EXT_BUSINESS_HOTSELL,
  EXT_HOTSELL_MODE_FETCH_PRODUCT_RSC,
  EXT_HOTSELL_MODE_LIST_COLLECT,
  type HotsaleFillConfig,
  type HotsellFetchProductRscResult,
  type HotsellStartPayload,
} from '@/constants/extension';
import { getAdminSystemConfig } from '@/services/admin/auth';
import {
  deleteMissionHotsaleData,
  extractMissionHotsaleData,
  fetchMissionHotsaleDataList,
  importMissionHotsaleData,
  markMissionHotsaleDataFinished,
} from '@/services/admin/missions';
import type {
  HotsaleCollectStatus,
  MissionHotsaleDataExtractResult,
  MissionHotsaleDataPublic,
} from '@/types/api';
import { formatDateTime } from '@/utils/datetime';
import {
  pingExtension,
  requestExtension,
  subscribeExtensionMessages,
} from '@/utils/extensionBridge';
import { parseHotsellRankResponse } from '@/utils/hotsellRank';

type ExtractUiPhase = 'idle' | 'pick_interval' | 'running';

const EXECUTABLE_COLLECT_STATUSES = new Set(['pending', 'failed']);

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

/** 拉取任务下全部 pending + failed（分页拼齐） */
async function fetchAllExecutableHotsaleRows(
  missionId: number,
): Promise<MissionHotsaleDataPublic[]> {
  const out: MissionHotsaleDataPublic[] = [];
  for (const collect_status of ['pending', 'failed'] as const) {
    let page = 1;
    for (;;) {
      const result = await fetchMissionHotsaleDataList({
        mission_id: missionId,
        collect_status,
        page,
        page_size: 100,
      });
      out.push(...result.items);
      if (result.items.length === 0 || page * 100 >= result.total) {
        break;
      }
      page += 1;
    }
  }
  out.sort((a, b) => {
    const ra = a.rank_no ?? Number.MAX_SAFE_INTEGER;
    const rb = b.rank_no ?? Number.MAX_SAFE_INTEGER;
    if (ra !== rb) {
      return ra - rb;
    }
    return a.id - b.id;
  });
  return out;
}

type TableParams = {
  current?: number;
  pageSize?: number;
  keyword?: string;
  collect_status?: string;
};

const COLLECT_STATUS_COLOR: Record<HotsaleCollectStatus, string> = {
  pending: 'processing',
  success: 'success',
  failed: 'error',
  marked_finished: 'warning',
};

const COLLECT_STATUS_LABEL: Record<HotsaleCollectStatus, string> = {
  pending: '进行中',
  success: '已完成',
  failed: '失败',
  marked_finished: '标记结束',
};

function renderProductLink(
  text: string | null | undefined,
  productUrl: string | null | undefined,
) {
  const label = (text || '').trim();
  if (!label) {
    return '-';
  }
  if (!productUrl) {
    return (
      <Typography.Text style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
        {label}
      </Typography.Text>
    );
  }
  return (
    <Typography.Link
      href={productUrl}
      target="_blank"
      rel="noreferrer"
      style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}
    >
      {label}
    </Typography.Link>
  );
}

/**
 * 设置任务数据表格：工具栏「开始采集」；扩展回传后入库并刷新列表。
 */
export function HotsaleDataTable({
  missionId,
  editable = false,
  onImported,
  onExtracted,
}: {
  missionId: number;
  supplierId?: number;
  editable?: boolean;
  /** 采集入库成功后回调（用于刷新任务状态等） */
  onImported?: (result: {
    created: number;
    mission_status: string;
  }) => void;
  /** 提取完成后回调（用于按 mission_status 刷新任务信息） */
  onExtracted?: (result: MissionHotsaleDataExtractResult) => void;
}) {
  const { message, modal } = App.useApp();
  const actionRef = useRef<ActionType | null>(null);
  const extractingRef = useRef(false);
  /** 多条提取：选完间隔后要跑的队列 */
  const pendingRecordsRef = useRef<MissionHotsaleDataPublic[] | null>(null);
  const [collecting, setCollecting] = useState(false);
  /** idle | 选间隔 | 串行提取中 */
  const [extractPhase, setExtractPhase] = useState<ExtractUiPhase>('idle');
  const [intervalSec, setIntervalSec] = useState(2);
  const [extractProgress, setExtractProgress] = useState<{
    done: number;
    total: number;
    intervalSec: number;
  } | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [selectedRows, setSelectedRows] = useState<MissionHotsaleDataPublic[]>(
    [],
  );
  const [batchLoading, setBatchLoading] = useState(false);

  const extracting = extractPhase !== 'idle';

  const clearSelection = useCallback(() => {
    setSelectedRowKeys([]);
    setSelectedRows([]);
  }, []);

  const resolveSelectedIds = useCallback(() => {
    return selectedRowKeys
      .map((k) => Number(k))
      .filter((n) => Number.isFinite(n) && n > 0);
  }, [selectedRowKeys]);

  const tipExtractResult = useCallback(
    (result: MissionHotsaleDataExtractResult) => {
      const total = result.success_count + result.fail_count;
      let text = `共计提取 ${total} 条，成功 ${result.success_count} 条，失败 ${result.fail_count} 条`;
      if (result.mission_status === 'running') {
        text += '；任务进行中';
      } else if (result.mission_finished || result.mission_status === 'finished') {
        text += '；任务已全部完成';
      }
      if (result.fail_count > 0 && result.success_count > 0) {
        message.warning(text);
      } else if (result.fail_count > 0) {
        message.error(text);
      } else {
        message.success(text);
      }
    },
    [message],
  );

  const loadFillConfig = useCallback(async (): Promise<HotsaleFillConfig> => {
    const configMap = await getAdminSystemConfig({ skipErrorHandler: true });
    const hotsaleRoot = asMissionHotsaleDhConfig(
      configMap[CONFIG_KEY_MISSION_HOTSALE_DH],
    );
    return hotsaleRoot?.fillConfig ?? {};
  }, []);

  /** 插件拉 Flight 原文；失败返回 null（批量时不逐条 toast，结束统一汇总） */
  const fetchFlightViaExtension = useCallback(
    async (
      productUrl: string,
      fillConfig: HotsaleFillConfig,
    ): Promise<string | null> => {
      const reply = await requestExtension(
        {
          businessType: EXT_BUSINESS_HOTSELL,
          action: 'START',
          payload: {
            mode: EXT_HOTSELL_MODE_FETCH_PRODUCT_RSC,
            openUrl: productUrl,
            fillConfig,
          } satisfies HotsellStartPayload,
        },
        30000,
      );
      if (!reply) {
        console.warn('[hotsale fetch_product_rsc] 插件无响应', productUrl);
        return null;
      }
      if (reply.action === 'ERROR') {
        console.warn('[hotsale fetch_product_rsc] 插件错误', reply.payload);
        return null;
      }
      const extResult = reply.payload as HotsellFetchProductRscResult | undefined;
      const flight = (extResult?.flightContent || '').trim();
      if (!extResult?.ok || !flight) {
        console.warn(
          '[hotsale fetch_product_rsc] 无 Flight',
          productUrl,
          extResult?.message,
        );
        return null;
      }
      console.log('[hotsale fetch_product_rsc] raw flight', {
        productUrl,
        httpStatus: extResult.httpStatus,
        contentType: extResult.contentType,
        elapsedMs: extResult.elapsedMs,
        flightContent: flight,
      });
      return flight;
    },
    [],
  );

  /**
   * 串行：插件拉数 → extract(flight_content) 入库。
   * 仅多条时展示进度并应用 gapSec；单条只显示加载态。
   */
  const runPluginExtractQueue = useCallback(
    async (records: MissionHotsaleDataPublic[], gapSec: number) => {
      if (extractingRef.current) {
        return;
      }
      if (!records.length) {
        message.warning('没有可提取的任务数据');
        return;
      }

      const showProgress = records.length > 1;
      extractingRef.current = true;
      setExtractPhase('running');
      setExtractProgress(
        showProgress
          ? { done: 0, total: records.length, intervalSec: gapSec }
          : null,
      );

      const installed = await pingExtension();
      if (!installed) {
        message.warning('请先安装对应的采集插件');
        extractingRef.current = false;
        setExtractPhase('idle');
        setExtractProgress(null);
        pendingRecordsRef.current = null;
        return;
      }

      let fillConfig: HotsaleFillConfig;
      try {
        fillConfig = await loadFillConfig();
      } catch {
        message.error('读取热卖配置失败');
        extractingRef.current = false;
        setExtractPhase('idle');
        setExtractProgress(null);
        pendingRecordsRef.current = null;
        return;
      }

      let successCount = 0;
      let failCount = 0;
      let lastResult: MissionHotsaleDataExtractResult | null = null;

      try {
        for (let i = 0; i < records.length; i += 1) {
          if (i > 0 && gapSec > 0) {
            await sleep(gapSec * 1000);
          }
          const record = records[i];
          const productUrl = (record.product_url || '').trim();
          if (!productUrl) {
            failCount += 1;
            if (showProgress) {
              setExtractProgress({
                done: i + 1,
                total: records.length,
                intervalSec: gapSec,
              });
            }
            continue;
          }

          const flight = await fetchFlightViaExtension(productUrl, fillConfig);
          if (!flight) {
            failCount += 1;
            if (showProgress) {
              setExtractProgress({
                done: i + 1,
                total: records.length,
                intervalSec: gapSec,
              });
            }
            continue;
          }

          try {
            const result = await extractMissionHotsaleData({
              mission_data_ids: [record.id],
              flight_content: flight,
            });
            lastResult = result;
            successCount += result.success_count;
            failCount += result.fail_count;
          } catch {
            failCount += 1;
          }

          if (showProgress) {
            setExtractProgress({
              done: i + 1,
              total: records.length,
              intervalSec: gapSec,
            });
          }
        }

        const summary: MissionHotsaleDataExtractResult = {
          success_count: successCount,
          fail_count: failCount,
          skipped_count: 0,
          fails: lastResult?.fails ?? [],
          mission_id: lastResult?.mission_id ?? missionId,
          mission_finished: lastResult?.mission_finished ?? false,
          mission_status: lastResult?.mission_status ?? null,
        };
        tipExtractResult(summary);
        onExtracted?.(summary);
        clearSelection();
        actionRef.current?.reload();
      } finally {
        extractingRef.current = false;
        setExtractPhase('idle');
        setExtractProgress(null);
        pendingRecordsRef.current = null;
      }
    },
    [
      clearSelection,
      fetchFlightViaExtension,
      loadFillConfig,
      message,
      missionId,
      onExtracted,
      tipExtractResult,
    ],
  );

  /**
   * 单条：直接跑（无间隔、无进度）。
   * 多条：先弹间隔选择，确认后再跑。
   */
  const startExtractFlow = useCallback(
    async (records: MissionHotsaleDataPublic[]) => {
      // 仅用 ref 防重入：任务提取拉列表时 phase 可能已是 running
      if (extractingRef.current) {
        return;
      }
      if (!records.length) {
        message.warning('没有可提取的任务数据');
        return;
      }
      if (records.length === 1) {
        await runPluginExtractQueue(records, 0);
        return;
      }
      pendingRecordsRef.current = records;
      setIntervalSec(2);
      setExtractProgress(null);
      setExtractPhase('pick_interval');
    },
    [message, runPluginExtractQueue],
  );

  const handleBatchMarkFinished = useCallback(async () => {
    const ids = resolveSelectedIds();
    if (!ids.length) {
      message.warning('请先选择任务数据');
      return;
    }
    setBatchLoading(true);
    try {
      await markMissionHotsaleDataFinished({
        id: ids,
        mission_id: missionId,
      });
      message.success(`已标记结束 ${ids.length} 条`);
      clearSelection();
      actionRef.current?.reload();
    } catch {
      // 错误已由全局拦截器处理
    } finally {
      setBatchLoading(false);
    }
  }, [clearSelection, message, missionId, resolveSelectedIds]);

  const handleBatchDelete = useCallback(async () => {
    const ids = resolveSelectedIds();
    if (!ids.length) {
      message.warning('请先选择任务数据');
      return;
    }
    setBatchLoading(true);
    try {
      await deleteMissionHotsaleData({
        id: ids,
        mission_id: missionId,
      });
      message.success(`已删除 ${ids.length} 条`);
      clearSelection();
      actionRef.current?.reload();
    } catch {
      // 错误已由全局拦截器处理
    } finally {
      setBatchLoading(false);
    }
  }, [clearSelection, message, missionId, resolveSelectedIds]);

  useEffect(() => {
    return subscribeExtensionMessages((msg) => {
      if (
        msg.businessType !== EXT_BUSINESS_HOTSELL ||
        msg.action !== 'SYNC_CONFIRM'
      ) {
        return;
      }
      console.log('[hotsell] SYNC_CONFIRM payload:', msg.payload);

      const payload =
        msg.payload && typeof msg.payload === 'object'
          ? (msg.payload as Record<string, unknown>)
          : null;
      if (!payload) {
        message.error('采集回传数据为空');
        return;
      }

      void (async () => {
        try {
          const result = await importMissionHotsaleData({
            mission_id: missionId,
            payload,
          });
          const summary = parseHotsellRankResponse(payload);
          const cate = result.cate_name || summary?.currentCategory || '未知';
          const count = result.total || summary?.itemCount || 0;
          modal.success({
            title: '采集完成',
            content: `已采集到 ${cate} 分类下 ${count} 条热卖数据`,
            okText: '知道了',
          });
          actionRef.current?.reload();
          onImported?.({
            created: result.created,
            mission_status: result.mission_status,
          });
        } catch (err) {
          message.error(
            err instanceof Error ? err.message : '热卖数据采集入库失败',
          );
        }
      })();
    });
  }, [message, missionId, modal, onImported]);

  const sendStartToExtension = useCallback(
    async (payload: HotsellStartPayload, successText: string) => {
      const installed = await pingExtension();
      if (!installed) {
        message.warning('请先安装对应的采集插件');
        return false;
      }

      const reply = await requestExtension(
        {
          businessType: EXT_BUSINESS_HOTSELL,
          action: 'START',
          payload,
        },
        3000,
      );

      if (!reply) {
        message.error('采集插件无响应，请确认插件已启用后重试');
        return false;
      }

      if (reply.action === 'ERROR') {
        const errPayload = reply.payload as { message?: string } | undefined;
        message.error(errPayload?.message || '采集插件返回错误');
        return false;
      }

      const result = reply.payload as
        | { ok?: boolean; message?: string }
        | undefined;
      if (result && result.ok === false) {
        message.warning(result.message || '采集插件暂未就绪，请升级扩展');
        return false;
      }

      message.success(successText);
      return true;
    },
    [message],
  );

  const handleStartCollect = useCallback(async () => {
    setCollecting(true);
    try {
      const configMap = await getAdminSystemConfig({ skipErrorHandler: true });
      const hotsaleRoot = asMissionHotsaleDhConfig(
        configMap[CONFIG_KEY_MISSION_HOTSALE_DH],
      );
      const collectConfig = hotsaleRoot?.collectConfig;
      if (
        !collectConfig ||
        typeof collectConfig.openUrl !== 'string' ||
        typeof collectConfig.watchApiUrl !== 'string'
      ) {
        message.error('未获取到热卖列表采集配置（collectConfig），请稍后重试');
        return;
      }

      await sendStartToExtension(
        {
          mode: EXT_HOTSELL_MODE_LIST_COLLECT,
          collectConfig,
        },
        '已向采集插件发起列表采集',
      );
    } catch {
      message.error('开始采集失败，请稍后重试');
    } finally {
      setCollecting(false);
    }
  }, [message, sendStartToExtension]);

  /** 单个提取：始终单条，直接加载态跑插件入库 */
  const handleExtractOne = useCallback(
    async (record: MissionHotsaleDataPublic) => {
      const productUrl = (record.product_url || '').trim();
      if (!productUrl) {
        message.warning('当前商品缺少产品链接，无法提取');
        return;
      }
      if (!EXECUTABLE_COLLECT_STATUSES.has(String(record.collect_status))) {
        message.warning('仅进行中或失败的数据可提取');
        return;
      }
      await startExtractFlow([record]);
    },
    [message, startExtractFlow],
  );

  /** 间隔确认后：对已缓存的多条队列串行提取 */
  const handleConfirmInterval = useCallback(async () => {
    const records = pendingRecordsRef.current;
    if (!records?.length) {
      setExtractPhase('idle');
      pendingRecordsRef.current = null;
      return;
    }
    const gap = Number.isFinite(intervalSec) ? Math.max(0, intervalSec) : 2;
    pendingRecordsRef.current = null;
    await runPluginExtractQueue(records, gap);
  }, [intervalSec, runPluginExtractQueue]);

  const handleCancelIntervalPicker = useCallback(() => {
    if (extractPhase !== 'pick_interval') {
      return;
    }
    setExtractPhase('idle');
    pendingRecordsRef.current = null;
  }, [extractPhase]);

  /**
   * 任务提取：先拉 pending/failed；单条直接跑，多条再选间隔。
   */
  const handleExtractMission = useCallback(async () => {
    if (extractingRef.current || extractPhase !== 'idle') {
      return;
    }
    // 拉列表期间用简单加载态（不展示进度）
    setExtractPhase('running');
    setExtractProgress(null);
    try {
      const records = await fetchAllExecutableHotsaleRows(missionId);
      if (!records.length) {
        setExtractPhase('idle');
        message.warning('当前任务没有可提取的进行中/失败数据');
        return;
      }
      // 单条会继续 running；多条会切到选间隔
      await startExtractFlow(records);
    } catch (err) {
      setExtractPhase('idle');
      message.error(
        err instanceof Error ? err.message : '准备提取列表失败，请稍后重试',
      );
    }
  }, [extractPhase, message, missionId, startExtractFlow]);

  /** 批量提取：可提取行单条直接跑，多条再选间隔 */
  const handleExtractSelected = useCallback(() => {
    if (!selectedRows.length) {
      message.warning('请先选择任务数据');
      return;
    }
    const records = selectedRows.filter((r) =>
      EXECUTABLE_COLLECT_STATUSES.has(String(r.collect_status)),
    );
    if (!records.length) {
      message.warning('请选择进行中或失败的任务数据');
      return;
    }
    void startExtractFlow(records);
  }, [message, selectedRows, startExtractFlow]);

  const statusLabel = (status: string) =>
    COLLECT_STATUS_LABEL[status as HotsaleCollectStatus] ?? status;

  const columns: ProColumns<MissionHotsaleDataPublic>[] = [
    {
      title: '搜索内容',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '产品名称 / 商品编码 / 店铺名称',
        allowClear: true,
      },
    },
    {
      title: '任务数据状态',
      dataIndex: 'collect_status',
      hideInTable: true,
      valueType: 'select',
      initialValue: 'all',
      fieldProps: {
        allowClear: false,
      },
      valueEnum: {
        all: { text: '全部' },
        pending: { text: '进行中' },
        success: { text: '已完成' },
        failed: { text: '失败' },
        marked_finished: { text: '标记结束' },
      },
    },
    {
      title: '排名',
      dataIndex: 'rank_no',
      width: 72,
      search: false,
    },
    {
      title: '产品编码',
      dataIndex: 'item_code',
      width: 130,
      search: false,
      render: (_, record) => {
        const status = record.collect_status as HotsaleCollectStatus;
        const failMsg =
          status === 'failed' ? (record.collect_msg || '').trim() : '';
        return (
          <div style={{ lineHeight: 1.5 }}>
            <div>{(record.item_code || '').trim() || '-'}</div>
            <div style={{ marginTop: 4 }}>
              <Tag color={COLLECT_STATUS_COLOR[status] ?? 'default'}>
                <span>{statusLabel(record.collect_status)}</span>
                {failMsg ? (
                  <Tooltip title={failMsg}>
                    <InfoCircleOutlined style={{ marginLeft: 4 }} />
                  </Tooltip>
                ) : null}
              </Tag>
            </div>
          </div>
        );
      },
    },
    {
      title: '主图',
      dataIndex: 'main_image_url',
      width: 72,
      search: false,
      render: (_, record) =>
        record.main_image_url ? (
          <Image
            src={record.main_image_url}
            width={48}
            height={48}
            style={{ objectFit: 'cover' }}
          />
        ) : (
          '-'
        ),
    },
    {
      title: '产品名称',
      dataIndex: 'product_name',
      search: false,
      ellipsis: false,
      render: (_, record) => {
        const name =
          (record.product_name || '').trim() ||
          (record.product_name_short || '').trim();
        if (!name) {
          return '-';
        }
        return (
          <span style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
            {renderProductLink(name, record.product_url)}
            <Typography.Text
              copyable={{ text: name, tooltips: ['复制', '已复制'] }}
              style={{ marginLeft: 4 }}
            />
          </span>
        );
      },
    },
    {
      title: '指标',
      dataIndex: 'deal',
      width: 140,
      search: false,
      render: (_, record) => (
        <div style={{ lineHeight: 1.55, fontSize: 12 }}>
          <div>成交量：{record.deal || '-'}</div>
          <div>成交金额：{record.deal_amount || '-'}</div>
          <div>成交人数：{record.deal_persons || '-'}</div>
        </div>
      ),
    },
    {
      title: '类目',
      dataIndex: 'cate_name',
      search: false,
      ellipsis: false,
      render: (_, record) => {
        const text = (record.cate_name || '').trim();
        if (!text) {
          return '-';
        }
        return (
          <span style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
            {text}
            <Typography.Text
              copyable={{ text, tooltips: ['复制', '已复制'] }}
              style={{ marginLeft: 4 }}
            />
          </span>
        );
      },
    },
    {
      title: '店铺名称',
      dataIndex: 'store_name',
      search: false,
      ellipsis: false,
      render: (_, record) => {
        const text = (record.store_name || '').trim();
        if (!text) {
          return '-';
        }
        return (
          <span style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
            {text}
            <Typography.Text
              copyable={{ text, tooltips: ['复制', '已复制'] }}
              style={{ marginLeft: 4 }}
            />
          </span>
        );
      },
    },
    {
      title: '操作',
      dataIndex: 'option',
      valueType: 'option' as const,
      search: false as const,
      width: editable ? 220 : 160,
      fixed: 'right',
      render: (_: unknown, record: MissionHotsaleDataPublic) => {
        // 已完成：操作列展示提取时间
        if (record.collect_status === 'success') {
          const timeText = formatDateTime(record.updated_at) || '-';
          return (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {`提取时间${timeText}`}
            </Typography.Text>
          );
        }

        const actions: React.ReactNode[] = [];

        if (
          editable &&
          (record.collect_status === 'pending' ||
            record.collect_status === 'failed')
        ) {
          actions.push(
            <Button
              key="extract-one"
              type="primary"
              size="small"
              shape="round"
              disabled={extracting}
              onClick={() => void handleExtractOne(record)}
            >
              单个提取
            </Button>,
          );
        }

        if (editable) {
          if (record.collect_status !== 'marked_finished') {
            actions.push(
              <Popconfirm
                key="finish"
                title="确认将这条任务数据标记结束？"
                onConfirm={async () => {
                  try {
                    await markMissionHotsaleDataFinished({
                      id: record.id,
                      mission_id: missionId,
                    });
                    message.success('已标记结束');
                    actionRef.current?.reload();
                  } catch {
                    // 错误已由全局拦截器处理
                  }
                }}
              >
                <Button type="primary" danger size="small" shape="round">
                  标记结束
                </Button>
              </Popconfirm>,
            );
          }
          actions.push(
            <Popconfirm
              key="delete"
              title="确认删除这条任务数据？"
              onConfirm={async () => {
                try {
                  await deleteMissionHotsaleData({
                    id: record.id,
                    mission_id: missionId,
                  });
                  message.success('已删除');
                  actionRef.current?.reload();
                } catch {
                  // 错误已由全局拦截器处理
                }
              }}
            >
              <Button danger size="small" shape="round">
                删除
              </Button>
            </Popconfirm>,
          );
        }

        if (!actions.length) {
          return null;
        }

        return (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, max-content)',
              gap: 8,
              justifyContent: 'start',
              alignItems: 'center',
            }}
          >
            {actions}
          </div>
        );
      },
    },
  ];

  return (
    <>
      <Modal
        open={extractPhase === 'pick_interval'}
        title="批量提取间隔"
        okText="开始提取"
        cancelText="取消"
        maskClosable={false}
        keyboard={false}
        centered
        width={420}
        onOk={() => void handleConfirmInterval()}
        onCancel={handleCancelIntervalPicker}
      >
        <div style={{ paddingTop: 8 }}>
          <div style={{ marginBottom: 12 }}>
            请选择批量运行时每条数据的间隔时间：
          </div>
          <Space>
            <InputNumber
              min={0}
              precision={0}
              value={intervalSec}
              onChange={(v) => setIntervalSec(typeof v === 'number' ? v : 0)}
              addonAfter="秒"
              style={{ width: 160 }}
            />
            <Typography.Text type="secondary">默认 2 秒，最小 0 秒</Typography.Text>
          </Space>
        </div>
      </Modal>
      <Modal
        open={extractPhase === 'running'}
        title={null}
        footer={null}
        closable={false}
        maskClosable={false}
        keyboard={false}
        centered
        width={
          extractProgress && extractProgress.total > 1 ? 320 : 280
        }
        styles={{ body: { padding: '32px 24px' } }}
      >
        <div style={{ textAlign: 'center' }}>
          {extractProgress && extractProgress.total > 1 ? (
            <div style={{ marginBottom: 16, lineHeight: 1.7 }}>
              <div>
                进度：{extractProgress.done} / {extractProgress.total}
              </div>
              <div style={{ color: 'rgba(0,0,0,0.45)', fontSize: 13 }}>
                单次间隔：{extractProgress.intervalSec} 秒
              </div>
            </div>
          ) : null}
          <Spin size="large" description="插件提取中..." />
        </div>
      </Modal>
      <ProTable<MissionHotsaleDataPublic, TableParams>
      headerTitle="任务数据"
      actionRef={actionRef}
      rowKey="id"
      search={{ labelWidth: 'auto' }}
      scroll={{ x: 1100 }}
      rowSelection={
        editable
          ? {
              selectedRowKeys,
              onChange: (keys, rows) => {
                setSelectedRowKeys(keys);
                setSelectedRows(rows);
              },
              getCheckboxProps: (record) => ({
                // 已完成不可删/不可标记结束
                disabled: record.collect_status === 'success',
              }),
            }
          : undefined
      }
      tableAlertOptionRender={() =>
        editable ? (
          <Space size={16}>
            <a
              onClick={() => {
                if (!extracting) {
                  void handleExtractSelected();
                }
              }}
              style={
                extracting || !selectedRowKeys.length
                  ? { pointerEvents: 'none', opacity: 0.45 }
                  : undefined
              }
            >
              批量提取
            </a>
            <Popconfirm
              title={`确认将选中的 ${selectedRowKeys.length} 条标记结束？`}
              disabled={!selectedRowKeys.length || batchLoading || extracting}
              onConfirm={() => void handleBatchMarkFinished()}
            >
              <a>批量标记结束</a>
            </Popconfirm>
            <Popconfirm
              title={`确认删除选中的 ${selectedRowKeys.length} 条？`}
              disabled={!selectedRowKeys.length || batchLoading || extracting}
              onConfirm={() => void handleBatchDelete()}
            >
              <a>批量删除</a>
            </Popconfirm>
            <a onClick={clearSelection}>取消选择</a>
          </Space>
        ) : (
          false
        )
      }
      toolBarRender={
        editable
          ? () => [
              <Button
                key="start-collect"
                type="primary"
                loading={collecting}
                disabled={extracting}
                onClick={() => void handleStartCollect()}
              >
                开始采集
              </Button>,
              <Button
                key="extract-mission"
                disabled={collecting || extracting}
                onClick={() => void handleExtractMission()}
              >
                任务提取
              </Button>,
            ]
          : false
      }
      pagination={{
        defaultPageSize: PAGE_SIZE_DEFAULT,
        pageSizeOptions: [10, 20, 50, 100],
        showSizeChanger: true,
      }}
      request={async (params) => {
        const keyword = params.keyword?.trim() || undefined;
        const statusRaw = (params.collect_status || '').trim();
        const collect_status =
          !statusRaw || statusRaw === 'all' ? undefined : statusRaw;
        const result = await fetchMissionHotsaleDataList({
          mission_id: missionId,
          page: params.current,
          page_size: params.pageSize,
          keyword,
          collect_status,
        });
        return {
          data: result.items,
          success: true,
          total: result.total,
        };
      }}
      columns={columns}
      locale={{
        emptyText: (
          <Empty description="暂无任务数据" />
        ),
      }}
    />
    </>
  );
}
