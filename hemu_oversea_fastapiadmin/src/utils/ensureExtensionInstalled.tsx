import { Button, Typography } from 'antd';
import type { ModalFuncProps } from 'antd';
import { CONFIG_KEY_EXTENSION_DOWNLOAD_URL } from '@/constants/extension';
import { getAdminSystemConfig } from '@/services/admin/auth';
import { pingExtension } from '@/utils/extensionBridge';

type ConfirmModalApi = {
  confirm: (config: ModalFuncProps) => {
    destroy: () => void;
    update: (config: ModalFuncProps) => void;
  };
};

async function resolveExtensionDownloadUrl(): Promise<string> {
  try {
    const configMap = await getAdminSystemConfig({ skipErrorHandler: true });
    const raw = configMap[CONFIG_KEY_EXTENSION_DOWNLOAD_URL];
    return typeof raw === 'string' ? raw.trim() : '';
  } catch {
    return '';
  }
}

function ExtensionInstallGuide({ downloadUrl }: { downloadUrl: string }) {
  return (
    <div>
      <Typography.Paragraph style={{ marginBottom: 12 }}>
        检测到您还没有安装采集插件。开始采集、提取商品等操作都需要先安装该插件，请按下面步骤操作：
      </Typography.Paragraph>
      <ol style={{ paddingLeft: 20, margin: 0, lineHeight: 2 }}>
        <li>
          点击下载插件安装包
          {downloadUrl ? (
            <>
              ：
              <Button
                type="link"
                href={downloadUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ paddingInline: 4, height: 'auto' }}
              >
                点击下载
              </Button>
            </>
          ) : (
            <Typography.Text type="secondary">
              （下载地址暂未配置，请联系管理员获取安装包）
            </Typography.Text>
          )}
        </li>
        <li>下载完成后，将 ZIP 压缩包解压到电脑上的任意文件夹</li>
        <li>
          打开 Chrome 浏览器，在地址栏输入{' '}
          <Typography.Text code>chrome://extensions</Typography.Text>{' '}
          并回车
        </li>
        <li>打开页面右上角的「开发者模式」</li>
        <li>
          点击「加载已解压的扩展程序」，选择刚才解压出来的那个文件夹
        </li>
        <li>
          列表中出现插件即表示安装成功，然后点击下方「我已安装」刷新本页即可继续操作
        </li>
      </ol>
    </div>
  );
}

/**
 * 检测采集插件是否已安装；未安装时居中弹出安装引导（含下载链接）。
 * @returns true=已安装可继续；false=未安装（用户取消或即将刷新）
 */
export async function ensureExtensionInstalled(
  modal: ConfirmModalApi,
): Promise<boolean> {
  const installed = await pingExtension();
  if (installed) {
    return true;
  }

  const downloadUrl = await resolveExtensionDownloadUrl();

  return new Promise((resolve) => {
    modal.confirm({
      title: '请先安装采集插件',
      centered: true,
      icon: null,
      width: 560,
      maskClosable: false,
      content: <ExtensionInstallGuide downloadUrl={downloadUrl} />,
      okText: '我已安装',
      cancelText: '取消',
      onOk: () => {
        window.location.reload();
        resolve(false);
      },
      onCancel: () => {
        resolve(false);
      },
    });
  });
}
