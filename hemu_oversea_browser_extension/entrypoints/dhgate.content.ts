import { parseHotsellRankResponse } from '../src/features/hotsell/parse-rank';
import {
  HOOK_SOURCE,
  onNetHookHit,
  requestInstallNetHook,
} from '../src/sites/dhgate/net-hook';
import {
  mountHotsellPanel,
  removeHotsellPanel,
} from '../src/sites/dhgate/ui-panel';

type PageReadyResult = {
  ok: boolean;
  active?: boolean;
  mode?: string;
  alertTip?: string;
  watchApiUrl?: string;
  hitCount?: number;
  hasLatest?: boolean;
};

type OpResult = {
  ok: boolean;
  message?: string;
  hitCount?: number;
  hasLatest?: boolean;
};

function sendInternal<T = unknown>(
  msg: Record<string, unknown>,
): Promise<T> {
  return chrome.runtime.sendMessage(msg) as Promise<T>;
}

/**
 * 敦煌站 isolated content：
 * 仅 list_collect 开页注入；面板展示用摘要解析 + 接口原文回传管理端。
 * fetch_product_rsc 在 background 直拉，不经过本页。
 */
export default defineContentScript({
  matches: ['*://*.dhgate.com/*'],
  runAt: 'document_idle',
  async main() {
    const ready = await sendInternal<PageReadyResult>({
      channel: 'hotsell',
      op: 'PAGE_READY',
    });

    if (!ready?.ok || !ready.active) {
      return;
    }

    // 非列表采集 Job（不应走到这里）；保守退出
    if (ready.mode && ready.mode !== 'list_collect') {
      return;
    }

    const panel = mountHotsellPanel(
      {
        alertTip: ready.alertTip || '请在本页完成热卖数据采集操作',
        hasLatest: false,
        requireLatest: true,
        confirmLabel: '完成采集',
      },
      {
        onConfirm: () => {
          void (async () => {
            panel.update({
              statusText: '正在回传管理端…',
            });
            const res = await sendInternal<OpResult>({
              channel: 'hotsell',
              op: 'CONFIRM',
            });
            if (res?.ok) {
              removeHotsellPanel();
            } else {
              panel.update({
                statusText: res?.message || '操作失败',
              });
            }
          })();
        },
        onCancel: () => {
          void (async () => {
            await sendInternal({ channel: 'hotsell', op: 'CANCEL' });
            removeHotsellPanel();
          })();
        },
      },
    );

    if (!ready.watchApiUrl) {
      return;
    }

    const watchApiUrl = ready.watchApiUrl;
    const install = () => requestInstallNetHook(watchApiUrl);
    install();
    const onMainReady = (event: MessageEvent) => {
      if (event.source !== window) return;
      if (
        event.data?.source === HOOK_SOURCE &&
        event.data?.op === 'MAIN_READY'
      ) {
        install();
      }
    };
    window.addEventListener('message', onMainReady);
    window.setTimeout(install, 300);
    window.setTimeout(install, 1000);

    onNetHookHit((detail) => {
      void (async () => {
        const summary = parseHotsellRankResponse(detail.data);
        const res = await sendInternal<OpResult>({
          channel: 'hotsell',
          op: 'API_HIT',
          data: detail.data,
          url: detail.url,
        });
        if (!res?.ok) return;

        if (summary) {
          panel.update({
            hasLatest: true,
            currentCategory: summary.currentCategory,
            itemCount: summary.itemCount,
            statusText: undefined,
          });
        } else {
          panel.update({
            hasLatest: true,
            currentCategory: '未知',
            itemCount: 0,
            statusText: undefined,
          });
        }
      })();
    });
  },
});
