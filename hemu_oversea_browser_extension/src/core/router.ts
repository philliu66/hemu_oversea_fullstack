import { EXTENSION_VERSION, EXT_SOURCE, PROTOCOL_VERSION } from '../shared/config';
import { hotsellFeature } from '../features/hotsell/manifest';
import {
  PLATFORM_BUSINESS,
  createExtMessage,
  type ExtMessage,
  type PongPayload,
} from './protocol';

export interface FeatureModule {
  businessType: string;
  /** 处理该业务下的消息；返回值会作为 reply payload 或整包 ExtMessage */
  handle(msg: ExtMessage, sender: chrome.runtime.MessageSender): Promise<unknown> | unknown;
}

const features = new Map<string, FeatureModule>();

export function registerFeature(feature: FeatureModule): void {
  features.set(feature.businessType, feature);
}

export function listSupportedBusinessTypes(): string[] {
  return [PLATFORM_BUSINESS, ...features.keys()];
}

/** 启动时注册内置 Feature */
export function bootstrapFeatures(): void {
  registerFeature(hotsellFeature);
}

/**
 * 统一路由：
 * - platform + PING → PONG（安装检测，按需）
 * - 其它 → 对应 Feature
 */
export async function routeMessage(
  msg: ExtMessage,
  sender: chrome.runtime.MessageSender,
): Promise<ExtMessage> {
  if (msg.version !== PROTOCOL_VERSION) {
    return createExtMessage({
      businessType: msg.businessType,
      action: 'ERROR',
      requestId: msg.requestId,
      sessionId: msg.sessionId,
      payload: {
        error: 'protocol_version_mismatch',
        expected: PROTOCOL_VERSION,
        got: msg.version,
      },
    });
  }

  // 安装检测：允许 businessType 为 platform，或任意类型但 action=PING
  if (msg.action === 'PING') {
    const payload: PongPayload = {
      extensionVersion: EXTENSION_VERSION,
      protocolVersion: PROTOCOL_VERSION,
      supportedBusinessTypes: listSupportedBusinessTypes(),
      detectMode: 'on_demand',
    };
    return createExtMessage({
      businessType: PLATFORM_BUSINESS,
      action: 'PONG',
      requestId: msg.requestId,
      sessionId: msg.sessionId,
      payload,
    });
  }

  if (msg.businessType === PLATFORM_BUSINESS) {
    return createExtMessage({
      businessType: PLATFORM_BUSINESS,
      action: 'ERROR',
      requestId: msg.requestId,
      payload: {
        error: 'unsupported_platform_action',
        message: `platform 仅支持 PING，收到 action=${msg.action}`,
      },
    });
  }

  const feature = features.get(msg.businessType);
  if (!feature) {
    return createExtMessage({
      businessType: msg.businessType,
      action: 'ERROR',
      requestId: msg.requestId,
      payload: {
        error: 'unknown_business_type',
        message: `未注册业务: ${msg.businessType}`,
        supportedBusinessTypes: listSupportedBusinessTypes(),
      },
    });
  }

  try {
    const result = await feature.handle(msg, sender);
    // Feature 若已返回完整信封则透传
    if (
      result &&
      typeof result === 'object' &&
      (result as ExtMessage).source === EXT_SOURCE &&
      (result as ExtMessage).action
    ) {
      return result as ExtMessage;
    }
    return createExtMessage({
      businessType: msg.businessType,
      action: msg.action === 'START' || msg.action === 'STOP' ? 'STATUS' : msg.action,
      requestId: msg.requestId,
      sessionId: msg.sessionId,
      payload: result,
    });
  } catch (err) {
    return createExtMessage({
      businessType: msg.businessType,
      action: 'ERROR',
      requestId: msg.requestId,
      sessionId: msg.sessionId,
      payload: {
        error: 'feature_handler_error',
        message: err instanceof Error ? err.message : String(err),
      },
    });
  }
}
