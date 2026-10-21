import type { FeatureModule } from '../../core/router';
import { startHotsellJob, stopListCapture } from './list-capture';

/**
 * 热卖采集 Feature
 * - list_collect：列表采集（部分信息）
 * - detail_fill：单次补充（详细信息，业务逻辑预留）
 */
export const hotsellFeature: FeatureModule = {
  businessType: 'hotsell',
  async handle(msg, sender) {
    if (msg.action === 'STATUS') {
      return {
        ok: true,
        phase: 'B',
        ready: ['PING', 'START list_collect', 'START detail_fill', 'SYNC_CONFIRM'],
        pending: ['detail_fill business', 'FILL_CONFIRM'],
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
