import {
  DeleteOutlined,
  DiffOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useIntl } from '@umijs/max';
import {
  App,
  Button,
  Image,
  Modal,
  Popconfirm,
  Spin,
  Tooltip,
  Typography,
} from 'antd';
import React, { useRef, useState } from 'react';
import { tweakDhgateImage } from '@/services/common/utils';
import type { DhProductImgPublic } from '@/types/api';
import { buildDhImageUrl } from '@/utils/dhImage';
import './ProductImagesEditor.less';

type ProductImagesEditorProps = {
  images?: DhProductImgPublic[];
  storeId?: number;
  alt?: string;
  onChange?: (images: DhProductImgPublic[]) => void;
};

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

const ProductImagesEditor: React.FC<ProductImagesEditorProps> = ({
  images,
  storeId,
  alt,
  onChange,
}) => {
  const intl = useIntl();
  const { message } = App.useApp();
  const list = images || [];
  const [tweakingIndex, setTweakingIndex] = useState<number>();
  const [diffIndex, setDiffIndex] = useState<number>();
  const tweakingRef = useRef(false);

  const handleTweak = async (index: number) => {
    const current = list[index];
    if (!current?.img_url) {
      return;
    }
    if (!storeId) {
      message.warning(
        intl.formatMessage({
          id: 'pages.product.detail.images.storeRequired',
          defaultMessage: '请先选择店铺',
        }),
      );
      return;
    }
    if (tweakingRef.current) {
      return;
    }
    tweakingRef.current = true;
    setTweakingIndex(index);
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
        intl.formatMessage({
          id: 'pages.product.detail.images.tweakSuccess',
          defaultMessage: '图片已微调',
        }),
      );
    } catch {
      // 全局 request errorHandler 已提示
    } finally {
      setTweakingIndex(undefined);
      tweakingRef.current = false;
    }
  };

  const handleDelete = (index: number) => {
    if (diffIndex === index) {
      setDiffIndex(undefined);
    } else if (diffIndex !== undefined && diffIndex > index) {
      setDiffIndex(diffIndex - 1);
    }
    onChange?.(list.filter((_, i) => i !== index));
  };

  const diffImg = diffIndex !== undefined ? list[diffIndex] : undefined;
  const currentSrc = buildDhImageUrl(diffImg?.img_url);
  const originalSrc = buildDhImageUrl(diffImg?.original?.img_url);

  if (!list.length) {
    return (
      <>
        {intl.formatMessage({
          id: 'pages.product.detail.imagesEmpty',
          defaultMessage: '暂无图片',
        })}
      </>
    );
  }

  return (
    <>
      <Image.PreviewGroup>
        <div className="product-detail-img-list">
          {list.map((img, index) => {
            const src = buildDhImageUrl(img.img_url);
            if (!src) {
              return null;
            }
            const busy = tweakingIndex === index;
            const tweaked = hasTweakOriginal(img);
            return (
              <div
                key={img.img_md5 || img.img_url || String(index)}
                className={`product-detail-img-tile${busy ? ' is-busy' : ''}`}
              >
                <Image
                  src={src}
                  alt={alt}
                  width={96}
                  height={96}
                  preview={{ mask: false }}
                />
                <div className="product-detail-img-mask">
                  {busy ? (
                    <Spin size="small" />
                  ) : (
                    <>
                      <Tooltip
                        title={intl.formatMessage({
                          id: 'pages.product.detail.images.tweak',
                          defaultMessage: '微调',
                        })}
                      >
                        <Button
                          type="text"
                          size="small"
                          icon={<ExperimentOutlined />}
                          onClick={(event) => {
                            event.stopPropagation();
                            void handleTweak(index);
                          }}
                        />
                      </Tooltip>
                      {tweaked ? (
                        <Tooltip
                          title={intl.formatMessage({
                            id: 'pages.product.detail.images.diff',
                            defaultMessage: '查看不同',
                          })}
                        >
                          <Button
                            type="text"
                            size="small"
                            icon={<DiffOutlined />}
                            onClick={(event) => {
                              event.stopPropagation();
                              setDiffIndex(index);
                            }}
                          />
                        </Tooltip>
                      ) : null}
                      <Popconfirm
                        title={intl.formatMessage({
                          id: 'pages.product.detail.images.deleteConfirm',
                          defaultMessage: '确定删除该图片？',
                        })}
                        onConfirm={() => handleDelete(index)}
                      >
                        <Tooltip
                          title={intl.formatMessage({
                            id: 'pages.product.detail.images.delete',
                            defaultMessage: '删除图片',
                          })}
                        >
                          <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={(event) => event.stopPropagation()}
                          />
                        </Tooltip>
                      </Popconfirm>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Image.PreviewGroup>
      <Modal
        title={intl.formatMessage({
          id: 'pages.product.detail.images.diffTitle',
          defaultMessage: '图片对比',
        })}
        open={diffIndex !== undefined}
        footer={null}
        width={680}
        onCancel={() => setDiffIndex(undefined)}
        destroyOnHidden
      >
        <div className="product-detail-img-diff">
          <div className="product-detail-img-diff-item">
            <Typography.Text>
              {intl.formatMessage({
                id: 'pages.product.detail.images.current',
                defaultMessage: '现图片',
              })}
            </Typography.Text>
            {currentSrc ? (
              <Image src={currentSrc} alt={alt} />
            ) : null}
          </div>
          <div className="product-detail-img-diff-item">
            <Typography.Text>
              {intl.formatMessage({
                id: 'pages.product.detail.images.original',
                defaultMessage: '原图片',
              })}
            </Typography.Text>
            {originalSrc ? (
              <Image src={originalSrc} alt={alt} />
            ) : null}
          </div>
        </div>
      </Modal>
    </>
  );
};

export default ProductImagesEditor;
