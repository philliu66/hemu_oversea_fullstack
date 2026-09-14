import dayjs, { type ConfigType, type Dayjs } from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import {
  APP_DATE_FORMAT,
  APP_DATETIME_FORMAT,
  APP_TIMEZONE,
} from '@/constants/datetime';

let dayjsReady = false;

/** 初始化 dayjs 插件（应用入口调用一次即可） */
export function setupDayjs() {
  if (dayjsReady) {
    return;
  }
  dayjs.extend(relativeTime);
  dayjs.extend(utc);
  dayjs.extend(timezone);
  dayjs.tz.setDefault(APP_TIMEZONE);
  dayjsReady = true;
}

/**
 * 将后端 UTC 时间转到全局时区后格式化。
 * 空值返回 '-'，非法值原样返回。
 */
export function formatDateTime(
  value?: ConfigType | null,
  format: string = APP_DATETIME_FORMAT,
): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  const parsed = dayjs.utc(value);
  if (!parsed.isValid()) {
    return String(value);
  }
  return parsed.tz(APP_TIMEZONE).format(format);
}

/** 仅日期部分 */
export function formatDate(
  value?: ConfigType | null,
  format: string = APP_DATE_FORMAT,
): string {
  return formatDateTime(value, format);
}

/** 取得全局时区下的 dayjs 实例（已从 UTC 转换） */
export function toAppTime(value?: ConfigType | null): Dayjs | null {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  const parsed = dayjs.utc(value);
  if (!parsed.isValid()) {
    return null;
  }
  return parsed.tz(APP_TIMEZONE);
}

export { APP_TIMEZONE, APP_DATETIME_FORMAT, APP_DATE_FORMAT };
