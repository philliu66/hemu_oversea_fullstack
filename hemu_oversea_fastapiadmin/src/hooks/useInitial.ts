import { useModel } from '@umijs/max';

/**
 * 读取全局 initialState（currentUser、config 等）。
 * 等价于 `useModel('@@initialState')`。
 *
 * @example
 * const { initialState } = useInitial();
 * const appName = initialState?.config?.name;
 * const hotsale = initialState?.config?.mission_hotsale_dh_config;
 */
export function useInitial() {
  return useModel('@@initialState');
}
