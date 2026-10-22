import type { FeatureModule } from '../../core/router';
import { startHotsellJob, stopListCapture } from './list-capture';

/**
 * 热卖采集 Feature
 * - list_collect：列表采集（部分信息，开标签 + 页内确认）
 * - fetch_product_rsc：background 直拉商品 RSC Flight，同步回传（不开 tab）
 */
export const hotsellFeature: FeatureModule = {
  businessType: 'hotsell',
  async handle(msg, sender) {
    if (msg.action === 'STATUS') {
      return {
        ok: true,
        phase: 'B',
        ready: [
          'PING',
          'START list_collect',
          'START fetch_product_rsc',
          'SYNC_CONFIRM',
        ],
        pending: ['batch fetch_product_rsc queue', 'ITEM_UPSERT ingest'],
      };
    }
    if (msg.action === 'START') {
      return startHotsellJob(msg, sender);
    }
    if (msg.action === 'STOP') {
      return stopListCapture();
    }
    return {
      ok: false,
      error: 'unsupported_action',
      message: `hotsell 暂不支持 action=${msg.action}`,
    };
  },
};
