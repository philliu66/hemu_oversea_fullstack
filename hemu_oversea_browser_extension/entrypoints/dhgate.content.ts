import { parseHotsellRankResponse } from '../src/features/hotsell/parse-rank';
import type { HotsellJobMode } from '../src/features/hotsell/types';
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
  mode?: HotsellJobMode;
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
  reserved?: boolean;
};

function sendInternal<T = unknown>(
  msg: Record<string, unknown>,
): Promise<T> {
  return chrome.runtime.sendMessage(msg) as Promise<T>;
}

/**
 * 敦煌站 isolated content：
 * - list_collect：面板 + watchApiUrl 监听
 * - detail_fill：面板提示（补充业务逻辑预留）
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

    const mode: HotsellJobMode = ready.mode === 'detail_fill' ? 'detail_fill' : 'list_collect';
    const isFill = mode === 'detail_fill';

    const panel = mountHotsellPanel(
      {
        alertTip:
          ready.alertTip ||
          (isFill
            ? '请在本页完成热卖品详情补充'
            : '请在本页完成热卖数据采集操作'),
        hasLatest: false,
        requireLatest: !isFill,
        confirmLabel: isFill ? '完成补充' : '完成采集',
        statusText: isFill ? '单次补充业务逻辑待接入' : undefined,
      },
      {
        onConfirm: () => {
          void (async () => {
            panel.update({
              statusText: isFill ? '正在结束补充流程…' : '正在回传管理端…',
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

    // 仅列表采集安装接口监听
    if (!isFill && ready.watchApiUrl) {
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
    }
  },
});
