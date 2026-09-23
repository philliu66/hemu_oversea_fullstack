import { useIntl } from '@umijs/max';
import { App, Button, Image, Space, Upload } from 'antd';
import type { UploadProps } from 'antd';
import React, { useState } from 'react';
import { uploadDhgateImage } from '@/services/common/utils';
import { buildDhImageUrl } from '@/utils/dhImage';

type DhgateAttrPicUploadProps = {
  storeId?: number;
  value?: string | null;
  onChange?: (picUrl: string | null) => void;
  /** 禁用删除 */
  hideClear?: boolean;
  disabled?: boolean;
};

const DhgateAttrPicUpload: React.FC<DhgateAttrPicUploadProps> = ({
  storeId,
  value,
  onChange,
  hideClear = false,
  disabled = false,
}) => {
  const intl = useIntl();
  const { message } = App.useApp();
  const [uploading, setUploading] = useState(false);
  const src = buildDhImageUrl(value);

  const customRequest: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    if (!storeId) {
      message.warning(
        intl.formatMessage({
          id: 'pages.product.detail.images.storeRequired',
          defaultMessage: '请先选择店铺',
        }),
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
      const picUrl = data.img_url || null;
      if (!picUrl) {
        throw new Error('empty img_url');
      }
      onChange?.(picUrl);
      onSuccess?.(data);
      message.success(
        intl.formatMessage({
          id: 'pages.product.detail.specAttrs.uploadSuccess',
          defaultMessage: '图片上传成功',
        }),
      );
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error('upload failed'));
      message.error(
        intl.formatMessage({
          id: 'pages.product.detail.specAttrs.uploadFailed',
          defaultMessage: '图片上传失败',
        }),
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <Space wrap size={8}>
      {src ? (
        <Image
          src={src}
          alt="attr"
          width={48}
          height={48}
          style={{ objectFit: 'cover', borderRadius: 4 }}
        />
      ) : null}
      <Upload
        accept="image/*"
        showUploadList={false}
        customRequest={customRequest}
        disabled={disabled || uploading || !storeId}
      >
        <Button size="small" loading={uploading} disabled={disabled}>
          {intl.formatMessage({
            id: 'pages.product.detail.specAttrs.selectPic',
            defaultMessage: '选择图片',
          })}
        </Button>
      </Upload>
      {!hideClear && !disabled && value ? (
        <Button
          type="link"
          size="small"
          disabled={uploading}
          onClick={() => onChange?.(null)}
        >
          {intl.formatMessage({
            id: 'pages.product.detail.specAttrs.clearPic',
            defaultMessage: '清除图片',
          })}
        </Button>
      ) : null}
    </Space>
  );
};

export default DhgateAttrPicUpload;
