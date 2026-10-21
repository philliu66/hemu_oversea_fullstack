import type { FeatureModule } from '../../core/router';

/**
 * 新业务脚手架模板：复制本目录为 features/<name>，改 businessType，并在 router.bootstrapFeatures 注册。
 */
export const exampleFeature: FeatureModule = {
  businessType: '_example',
  async handle(msg) {
    return {
      ok: false,
      error: 'example_only',
      message: `示例 Feature，勿在生产注册。action=${msg.action}`,
    };
  },
};
