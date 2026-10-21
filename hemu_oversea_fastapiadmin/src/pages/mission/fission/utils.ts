export const MISSION_FISSION_PATH = '/mission/fission';
export const MISSION_TYPE_FISSION = 'fission_dh' as const;

export function missionFissionDataPath(id: number) {
  return `/mission/fission/${id}/data`;
}

export function missionFissionDetailPath(id: number) {
  return `/mission/fission/${id}`;
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
