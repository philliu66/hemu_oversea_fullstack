import {
  DiffOutlined,
  ExperimentOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { App, Image, Modal, Spin, Tooltip, Typography, Upload } from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  tweakDhgateImage,
  uploadDhgateImage,
} from '@/services/common/utils';
import { buildDhImageUrl } from '@/utils/dhImage';
import './ProductImagesEditor.less';

type AttrPicMeta = {
  img_url: string;
  img_md5?: string | null;
  original?: { img_url: string; img_md5?: string | null } | null;
};

type DhgateAttrPicUploadProps = {
  storeId?: number;
  value?: string | null;
  onChange?: (picUrl: string | null) => void;
  /** 禁用删除 */
  hideClear?: boolean;
  disabled?: boolean;
  /** 表格内紧凑单图（86px），已有图时不额外展示「重新上传」卡片 */
  compact?: boolean;
};

const FILE_UID = 'attr-pic';

/**
 * 规格/属性自定义图片：与产品图片同一套 picture-card 交互（单图）。
 * - 上传走 uploadimg，覆盖当前图
 * - 微调走 tweakimg，覆盖当前图
 */
const DhgateAttrPicUpload: React.FC<DhgateAttrPicUploadProps> = ({
  storeId,
  value,
  onChange,
  hideClear = false,
  disabled = false,
  compact = false,
}) => {
  const { message } = App.useApp();
  const [uploading, setUploading] = useState(false);
  const [tweaking, setTweaking] = useState(false);
  const [meta, setMeta] = useState<AttrPicMeta | null>(() =>
    value ? { img_url: value } : null,
  );
  const [diffOpen, setDiffOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSrc, setPreviewSrc] = useState('');
  const tweakingRef = useRef(false);

  useEffect(() => {
    const nextUrl = value?.trim() || '';
    setMeta((prev) => {
      if (!nextUrl) {
        return null;
      }
      if (prev?.img_url === nextUrl) {
        return prev;
      }
      // 外部写入新 url（非本组件微调产生）时，重置 original
      return { img_url: nextUrl };
    });
  }, [value]);

  const fileList: UploadFile[] = useMemo(() => {
    const url = buildDhImageUrl(meta?.img_url || value);
    if (!url) {
      return [];
    }
    return [
      {
        uid: FILE_UID,
        name: meta?.img_url || value || 'attr-image',
        status: 'done' as const,
        url,
      },
    ];
  }, [meta?.img_url, value]);

  const ensureStore = () => {
    if (storeId) {
      return true;
    }
    message.warning(
      '请先选择店铺',
    );
    return false;
  };

  const customRequest: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    if (!ensureStore()) {
      onError?.(new Error('store required'));
      return;
    }
    const raw = file as File;
    setUploading(true);
    try {
      const data = await uploadDhgateImage({
        store_id: storeId!,
        file: raw,
        filename: raw.name || 'upload.jpg',
      });
      const picUrl = data.img_url || null;
      if (!picUrl) {
        throw new Error('empty img_url');
      }
      setMeta({
        img_url: picUrl,
        img_md5: data.img_md5,
        original: null,
      });
      onChange?.(picUrl);
      onSuccess?.(data);
      message.success(
        '图片上传成功',
      );
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error('upload failed'));
      message.error(
        '图片上传失败',
      );
    } finally {
      setUploading(false);
    }
  };

  const handleTweak = async () => {
    const currentUrl = meta?.img_url || value;
    if (!currentUrl || disabled) {
      return;
    }
    if (!ensureStore()) {
      return;
    }
    if (tweakingRef.current) {
      return;
    }
    tweakingRef.current = true;
    setTweaking(true);
    try {
      const data = await tweakDhgateImage({
        store_id: storeId!,
        img_url: currentUrl,
        img_md5: meta?.img_md5,
      });
      const nextUrl = data.tweaked.img_url;
      if (!nextUrl) {
        throw new Error('empty tweaked img_url');
      }
      setMeta({
        img_url: nextUrl,
        img_md5: data.tweaked.img_md5,
        original:
          meta?.original ??
          data.original ?? {
            img_url: currentUrl,
            img_md5: meta?.img_md5,
          },
      });
      onChange?.(nextUrl);
      message.success(
        '图片已微调',
      );
    } catch {
      // 全局 request errorHandler 已提示
    } finally {
      setTweaking(false);
      tweakingRef.current = false;
    }
  };

  const handleRemove = () => {
    if (disabled || hideClear) {
      return false;
    }
    setMeta(null);
    onChange?.(null);
    return false;
  };

  const hasOriginal = Boolean(meta?.original?.img_url && meta?.img_url);
  const currentSrc = buildDhImageUrl(meta?.img_url || value);
  const originalSrc = buildDhImageUrl(meta?.original?.img_url);

  return (
    <>
      <Upload
        listType="picture-card"
        className={`product-detail-img-upload${compact ? ' is-compact' : ''}`}
        accept="image/*"
        maxCount={compact ? 1 : undefined}
        fileList={fileList}
        disabled={disabled || uploading || tweaking}
        customRequest={customRequest}
        onChange={() => undefined}
        onPreview={(file) => {
          if (!file.url) {
            return;
          }
          setPreviewSrc(file.url);
          setPreviewOpen(true);
        }}
        onRemove={handleRemove}
        onDownload={() => {
          if (disabled) {
            return;
          }
          void handleTweak();
        }}
        showUploadList={{
          showPreviewIcon: true,
          showRemoveIcon: !disabled && !hideClear,
          showDownloadIcon: !disabled && Boolean(meta?.img_url || value),
          downloadIcon: (
            <Tooltip
              title={'微调图片'}
            >
              <ExperimentOutlined
                className="product-detail-upload-tweak"
                style={{ color: '#fff' }}
              />
            </Tooltip>
          ),
        }}
        itemRender={(originNode) => (
          <div
            className={`product-detail-upload-item${tweaking ? ' is-busy' : ''}`}
          >
            {originNode}
            {tweaking ? (
              <div className="product-detail-upload-busy">
                <Spin size="small" />
              </div>
            ) : null}
            {hasOriginal && !tweaking ? (
              <Tooltip
                title={'查看不同'}
              >
                <button
                  type="button"
                  className="product-detail-upload-diff"
                  onClick={(event) => {
                    event.stopPropagation();
                    setDiffOpen(true);
                  }}
                >
                  <DiffOutlined />
                </button>
              </Tooltip>
            ) : null}
          </div>
        )}
      >
        {!disabled && (!compact || fileList.length < 1) ? (
          <button type="button" className="product-detail-upload-trigger">
            {uploading ? <Spin size="small" /> : <PlusOutlined />}
            <div style={{ marginTop: compact ? 4 : 8 }}>
              {!compact && fileList.length ? '重新上传' : '上传'}
            </div>
          </button>
        ) : null}
      </Upload>

      <Image
        style={{ display: 'none' }}
        preview={{
          visible: previewOpen,
          src: previewSrc,
          onVisibleChange: (visible) => setPreviewOpen(visible),
        }}
      />

      <Modal
        title={'图片对比'}
        open={diffOpen && hasOriginal}
        footer={null}
        width={680}
        onCancel={() => setDiffOpen(false)}
        destroyOnHidden
      >
        <div className="product-detail-img-diff">
          <div className="product-detail-img-diff-item">
            <Typography.Text>
              {'现图片'}
            </Typography.Text>
            {currentSrc ? <Image src={currentSrc} alt="attr" /> : null}
          </div>
          <div className="product-detail-img-diff-item">
            <Typography.Text>
              {'原图片'}
            </Typography.Text>
            {originalSrc ? <Image src={originalSrc} alt="attr" /> : null}
          </div>
        </div>
      </Modal>
    </>
  );
};

export default DhgateAttrPicUpload;
