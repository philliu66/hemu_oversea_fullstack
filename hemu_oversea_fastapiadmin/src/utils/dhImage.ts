const DEFAULT_DH_IMG_PREX = 'http://image.dhgate.com';

function getDhImgPrefix(): string {
  const raw = String(process.env.DH_IMG_PREX || DEFAULT_DH_IMG_PREX).trim();
  return raw.replace(/\/+$/, '') || DEFAULT_DH_IMG_PREX;
}

/** 相对路径补全敦煌图片前缀；已是完整 URL 则原样返回。 */
export function buildDhImageUrl(
  imgUrl?: string | null,
): string | undefined {
  const text = String(imgUrl || '').trim();
  if (!text) {
    return undefined;
  }
  if (/^https?:\/\//i.test(text)) {
    return text;
  }
  return `${getDhImgPrefix()}/${text.replace(/^\/+/, '')}`;
}
