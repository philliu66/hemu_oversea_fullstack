import type { HotsellJob } from './types';

/** 内存中的当前热卖任务；不落盘，进程内单例 */
let job: HotsellJob | null = null;

export function getHotsellJob(): HotsellJob | null {
  return job;
}

/** 整份替换当前任务（新 START 用新对象覆盖，不做字段级 merge） */
export function setHotsellJob(next: HotsellJob | null): void {
  job = next;
}

export function updateHotsellJob(
  patch: Partial<HotsellJob>,
): HotsellJob | null {
  if (!job) return null;
  job = { ...job, ...patch } as HotsellJob;
  return job;
}
