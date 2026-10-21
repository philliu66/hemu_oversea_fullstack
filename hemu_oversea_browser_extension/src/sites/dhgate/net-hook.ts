/**
 * 网络拦截：在页面主世界（MAIN）劫持 fetch / XHR。
 * 不要用 <script> 内联注入——敦煌等站点 CSP 常会静默拦截。
 *
 * 匹配规则：忽略 query / hash，按 origin + pathname 对齐；
 * 配置 `.../productrankNew.do` 可命中 `.../productrankNew.do?page=1&...`。
 */

export const HOOK_SOURCE = 'hemu-hotsell-page-hook';
/** isolated → MAIN：请求安装 hook */
export const HOOK_INSTALL_SOURCE = 'hemu-hotsell-install-hook';

export type HookHitDetail = {
  url: string;
  data: unknown;
  ts: number;
};

/** 判断请求 URL 是否命中监听地址（忽略 query/hash） */
export function matchWatchUrl(requestUrl: string, watchApiUrl: string): boolean {
  if (!requestUrl || !watchApiUrl) return false;
  try {
    const abs = new URL(String(requestUrl), location.href);
    const watch = new URL(String(watchApiUrl), location.href);
    if (abs.origin === watch.origin && abs.pathname === watch.pathname) {
      return true;
    }
    // 容错：pathname 以配置 pathname 结尾（偶发前缀差异）
    if (
      abs.origin === watch.origin &&
      (abs.pathname === watch.pathname ||
        abs.pathname.endsWith(watch.pathname))
    ) {
      return true;
    }
    const base = `${watch.origin}${watch.pathname}`;
    return abs.href.startsWith(base);
  } catch {
    const reqBase = String(requestUrl).split('?')[0].split('#')[0];
    const watchBase = String(watchApiUrl).split('?')[0].split('#')[0];
    return reqBase.includes(watchBase) || watchBase.includes(reqBase);
  }
}

/**
 * 在 MAIN world 执行：安装 fetch / XHR hook。
 * 由 `dhgate-main.content.ts` 调用。
 */
export function installNetHookInMainWorld(watchApiUrl: string): void {
  const flag = '__hemu_hotsell_net_hook__';
  const g = window as unknown as Record<string, unknown>;
  if (g[flag]) {
    // 已安装则更新监听目标
    g.__hemu_hotsell_watch__ = watchApiUrl;
    return;
  }
  g[flag] = true;
  g.__hemu_hotsell_watch__ = watchApiUrl;

  const matchUrl = (url: string) =>
    matchWatchUrl(url, String(g.__hemu_hotsell_watch__ || ''));

  const emit = (url: string, data: unknown) => {
    try {
      window.postMessage(
        { source: HOOK_SOURCE, url, data, ts: Date.now() },
        '*',
      );
    } catch {
      // ignore
    }
  };

  const parseBody = (text: string) => {
    if (text == null || text === '') return text;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  };

  const ofetch = window.fetch.bind(window);
  window.fetch = function hemuPatchedFetch(
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> {
    const url =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    return ofetch(input as RequestInfo, init).then((res) => {
      if (!matchUrl(url || res.url)) return res;
      try {
        void res
          .clone()
          .text()
          .then((text) => emit(res.url || url, parseBody(text)))
          .catch(() => undefined);
      } catch {
        // ignore
      }
      return res;
    });
  };

  const XO = window.XMLHttpRequest;
  const open = XO.prototype.open;
  const send = XO.prototype.send;
  XO.prototype.open = function hemuPatchedOpen(
    method: string,
    url: string | URL,
    ...rest: unknown[]
  ) {
    (this as XMLHttpRequest & { __hemuUrl?: string }).__hemuUrl = String(url);
    return open.apply(this, [method, url, ...rest] as Parameters<typeof open>);
  };
  XO.prototype.send = function hemuPatchedSend(
    body?: Document | XMLHttpRequestBodyInit | null,
  ) {
    const xhr = this as XMLHttpRequest & { __hemuUrl?: string };
    xhr.addEventListener('load', () => {
      const hitUrl = xhr.responseURL || xhr.__hemuUrl || '';
      if (!matchUrl(hitUrl)) return;
      emit(hitUrl, parseBody(xhr.responseText));
    });
    return send.call(this, body);
  };
}

/** isolated world：请 MAIN world 安装 / 更新 hook */
export function requestInstallNetHook(watchApiUrl: string): void {
  window.postMessage(
    {
      source: HOOK_INSTALL_SOURCE,
      op: 'INSTALL',
      watchApiUrl,
      ts: Date.now(),
    },
    '*',
  );
}

/** isolated world：监听 MAIN world 上报的命中 */
export function onNetHookHit(handler: (detail: HookHitDetail) => void): () => void {
  const listener = (event: MessageEvent) => {
    if (event.source !== window) return;
    const data = event.data;
    if (!data || data.source !== HOOK_SOURCE) return;
    if (data.op === 'MAIN_READY') return;
    handler({
      url: String(data.url || ''),
      data: data.data,
      ts: typeof data.ts === 'number' ? data.ts : Date.now(),
    });
  };
  window.addEventListener('message', listener);
  return () => window.removeEventListener('message', listener);
}
