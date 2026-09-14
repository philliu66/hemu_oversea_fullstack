/**
 * 新开窗口并以顶层方式加载授权链接（避免 iframe 公网回跳 localhost 被浏览器拦截）。
 * 返回 popup 引用；被拦截时返回 null。
 */
export function openAuthorizeWindow(authorizeUrl: string): Window | null {
  const popup = window.open(
    authorizeUrl,
    'hemu_store_oauth',
    'width=960,height=720,menubar=no,toolbar=no,location=yes,resizable=yes,scrollbars=yes',
  );
  return popup;
}
