import {
  DiffOutlined,
  ExperimentOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import {
  App,
  Image,
  Modal,
  Spin,
  Tooltip,
  Typography,
  Upload,
} from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import React, { useMemo, useRef, useState } from 'react';
import {
  tweakDhgateImage,
  uploadDhgateImage,
} from '@/services/common/utils';
import type { DhProductImgPublic } from '@/types/api';
import { buildDhImageUrl } from '@/utils/dhImage';
import './ProductImagesEditor.less';

type ProductImagesEditorProps = {
  images?: DhProductImgPublic[];
  storeId?: number;
  alt?: string;
  disabled?: boolean;
  onChange?: (images: DhProductImgPublic[]) => void;
};

/** uid 只跟列表下标绑定，微调改 md5/url 时不能变，否则 Upload 会叠出重复项 */
const IMG_UID_PREFIX = 'product-img-';

function cloneImg(img: DhProductImgPublic): DhProductImgPublic {
  return {
    img_url: img.img_url ?? null,
    img_md5: img.img_md5 ?? null,
    type: img.type ?? null,
  };
}

function hasTweakOriginal(img: DhProductImgPublic) {
  return Boolean(img.original?.img_url && img.img_url);
}

function getImgUid(_img: DhProductImgPublic, index: number) {
  return `${IMG_UID_PREFIX}${index}`;
}

function parseImgUid(uid: string): number {
  if (!uid.startsWith(IMG_UID_PREFIX)) {
    return -1;
  }
  const index = Number(uid.slice(IMG_UID_PREFIX.length));
  return Number.isInteger(index) && index >= 0 ? index : -1;
}

const ProductImagesEditor: React.FC<ProductImagesEditorProps> = ({
  images,
  storeId,
  alt,
  disabled = false,
  onChange,
}) => {
  const { message } = App.useApp();
  const list = images || [];
  const [tweakingUid, setTweakingUid] = useState<string>();
  const [uploading, setUploading] = useState(false);
  const [diffUid, setDiffUid] = useState<string>();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSrc, setPreviewSrc] = useState('');
  const tweakingRef = useRef(false);

  const fileList: UploadFile[] = useMemo(
    () =>
      list
        .map((img, index) => {
          const url = buildDhImageUrl(img.img_url);
          if (!url) {
            return null;
          }
          const uid = getImgUid(img, index);
          return {
            uid,
            name: img.img_url || `image-${index}`,
            status: 'done' as const,
            url,
          };
        })
        .filter((item): item is UploadFile => Boolean(item)),
    [list],
  );

  const findIndexByUid = (uid: string) => {
    const index = parseImgUid(uid);
    return index >= 0 && index < list.length ? index : -1;
  };

  const handleTweak = async (uid: string) => {
    const index = findIndexByUid(uid);
    const current = list[index];
    if (!current?.img_url) {
      return;
    }
    if (!storeId) {
      message.warning(
        '请先选择店铺',
      );
      return;
    }
    if (tweakingRef.current) {
      return;
    }
    tweakingRef.current = true;
    setTweakingUid(uid);
    try {
      const data = await tweakDhgateImage({
        store_id: storeId,
        img_url: current.img_url,
        img_md5: current.img_md5,
        type: current.type,
      });
      const next = list.map((img, i) => {
        if (i !== index) {
          return img;
        }
        return {
          img_url: data.tweaked.img_url,
          img_md5: data.tweaked.img_md5,
          type: data.tweaked.type ?? img.type,
          original: img.original ?? data.original ?? cloneImg(img),
        };
      });
      onChange?.(next);
      message.success(
        '图片已微调',
      );
    } catch {
      // 全局 request errorHandler 已提示
    } finally {
      setTweakingUid(undefined);
      tweakingRef.current = false;
    }
  };

  const handleDelete = (uid: string) => {
    if (diffUid === uid) {
      setDiffUid(undefined);
    }
    const index = findIndexByUid(uid);
    if (index < 0) {
      return;
    }
    onChange?.(list.filter((_, i) => i !== index));
  };

  const customRequest: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    if (!storeId) {
      message.warning(
        '请先选择店铺',
      );
      onError?.(new Error('store required'));
      return;
    }
    const raw = file as File;
    setUploading(true);
    try {
      const data = await uploadDhgateImage({
        store_id: storeId,
        file: raw,
        filename: raw.name || 'upload.jpg',
      });
      if (!data.img_url) {
        throw new Error('empty img_url');
      }
      onChange?.([
        ...list,
        {
          img_url: data.img_url,
          img_md5: data.img_md5,
          type: data.type ?? null,
        },
      ]);
      onSuccess?.(data);
      message.success(
        '图片上传成功',
      );
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error('upload failed'));
    } finally {
      setUploading(false);
    }
  };

  const diffIndex = diffUid ? findIndexByUid(diffUid) : -1;
  const diffImg = diffIndex >= 0 ? list[diffIndex] : undefined;
  const currentSrc = buildDhImageUrl(diffImg?.img_url);
  const originalSrc = buildDhImageUrl(diffImg?.original?.img_url);

  return (
    <>
      <Upload
        listType="picture-card"
        className="product-detail-img-upload"
        accept="image/*"
        multiple
        fileList={fileList}
        disabled={disabled || uploading}
        customRequest={customRequest}
        // 完全受控：列表只由 props/onChange(业务) 驱动，避免内部合并叠出重复项
        onChange={() => undefined}
        onPreview={(file) => {
          if (!file.url) {
            return;
          }
          setPreviewSrc(file.url);
          setPreviewOpen(true);
        }}
        onRemove={(file) => {
          if (disabled) {
            return false;
          }
          handleDelete(file.uid);
          // false：阻止 Upload 再改内部 fileList，删除结果以受控 props 为准
          return false;
        }}
        onDownload={(file) => {
          if (disabled) {
            return;
          }
          void handleTweak(file.uid);
        }}
        showUploadList={{
          showPreviewIcon: true,
          showRemoveIcon: !disabled,
          showDownloadIcon: !disabled,
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
        itemRender={(originNode, file) => {
          const index = findIndexByUid(file.uid);
          const img = index >= 0 ? list[index] : undefined;
          const busy = tweakingUid === file.uid;
          const tweaked = img ? hasTweakOriginal(img) : false;

          return (
            <div
              className={`product-detail-upload-item${busy ? ' is-busy' : ''}`}
            >
              {originNode}
              {busy ? (
                <div className="product-detail-upload-busy">
                  <Spin size="small" />
                </div>
              ) : null}
              {tweaked && !busy ? (
                <Tooltip
                  title={'查看不同'}
                >
                  <button
                    type="button"
                    className="product-detail-upload-diff"
                    onClick={(event) => {
                      event.stopPropagation();
                      setDiffUid(file.uid);
                    }}
                  >
                    <DiffOutlined />
                  </button>
                </Tooltip>
              ) : null}
            </div>
          );
        }}
      >
        {!disabled ? (
          <button type="button" className="product-detail-upload-trigger">
            {uploading ? <Spin size="small" /> : <PlusOutlined />}
            <div style={{ marginTop: 8 }}>
              {'上传图片'}
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
        open={Boolean(diffUid) && diffIndex >= 0}
        footer={null}
        width={680}
        onCancel={() => setDiffUid(undefined)}
        destroyOnHidden
      >
        <div className="product-detail-img-diff">
          <div className="product-detail-img-diff-item">
            <Typography.Text>
              {'现图片'}
            </Typography.Text>
            {currentSrc ? <Image src={currentSrc} alt={alt} /> : null}
          </div>
          <div className="product-detail-img-diff-item">
            <Typography.Text>
              {'原图片'}
            </Typography.Text>
            {originalSrc ? <Image src={originalSrc} alt={alt} /> : null}
          </div>
        </div>
      </Modal>
    </>
  );
};

export default ProductImagesEditor;
