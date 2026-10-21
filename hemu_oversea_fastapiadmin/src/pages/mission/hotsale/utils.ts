export const MISSION_HOTSALE_PATH = '/mission/hotsale';
export const MISSION_TYPE_HOTSALE = 'hotsale_dh' as const;

export function missionHotsaleDataPath(id: number) {
  return `/mission/hotsale/${id}/data`;
}

export function missionHotsaleDetailPath(id: number) {
  return `/mission/hotsale/${id}`;
}

export function parseMissionId(value?: string) {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

export function personLabel(
  nickname?: string | null,
  username?: string | null,
) {
  const name = nickname?.trim();
  const account = username?.trim();
  if (name && account && name !== account) {
    return `${name}（${account}）`;
  }
  return name || account || '-';
}
