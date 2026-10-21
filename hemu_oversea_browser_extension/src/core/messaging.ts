import type { ExtMessage } from './protocol';

/** background → 指定管理端 tab 的 content script */
export async function sendToTab(tabId: number, message: ExtMessage): Promise<unknown> {
  return chrome.tabs.sendMessage(tabId, message);
}

/** content script → background（Promise 封装） */
export function sendToBackground<T = unknown>(message: ExtMessage): Promise<T> {
  return chrome.runtime.sendMessage(message) as Promise<T>;
}
