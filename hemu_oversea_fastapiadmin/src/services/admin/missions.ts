import { request } from '@umijs/max';
import { AdminMissionApi } from '@/constants/api';
import type {
  ApiResponse,
  MissionCreateParams,
  MissionFissionDataAddParams,
  MissionFissionDataDetailPublic,
  MissionFissionDataPublic,
  MissionFissionDataUpdateParams,
  MissionListParams,
  MissionLogPublic,
  MissionPublic,
  MissionUpdateParams,
  PageData,
} from '@/types/api';
import { unwrapApiData } from '@/utils/http';

type RequestOptions = {
  skipErrorHandler?: boolean;
  [key: string]: unknown;
};

function requireData<T>(payload: T | null, message: string): T {
  if (payload === null || payload === undefined) {
    throw new Error(message);
  }
  return payload;
}

/** POST /api/v1/admin/missions/list */
export async function fetchMissionList(
  params: MissionListParams = {},
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<MissionPublic>>>(
    AdminMissionApi.LIST,
    {
      method: 'POST',
      data: {
        keyword: params.keyword,
        supplier_id: params.supplier_id,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<MissionPublic>>(res),
    '获取任务列表失败',
  );
}

/** POST /api/v1/admin/missions/detail */
export async function fetchMissionDetail(
  id: number,
  options?: RequestOptions & { supplier_id?: number },
) {
  const { supplier_id, ...rest } = options ?? {};
  const res = await request<ApiResponse<MissionPublic>>(
    AdminMissionApi.DETAIL,
    {
      method: 'POST',
      data: { id, supplier_id },
      ...rest,
    },
  );
  return requireData(unwrapApiData<MissionPublic>(res), '获取任务详情失败');
}

/** POST /api/v1/admin/missions/create */
export async function createMission(
  params: MissionCreateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<MissionPublic>>(
    AdminMissionApi.CREATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<MissionPublic>(res), '创建任务失败');
}

/** POST /api/v1/admin/missions/update */
export async function updateMission(
  params: MissionUpdateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<MissionPublic>>(
    AdminMissionApi.UPDATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(unwrapApiData<MissionPublic>(res), '更新任务失败');
}

/** POST /api/v1/admin/missions/mark-finished */
export async function markMissionFinished(id: number, options?: RequestOptions) {
  const res = await request<ApiResponse<MissionPublic>>(
    AdminMissionApi.MARK_FINISHED,
    {
      method: 'POST',
      data: { id },
      ...options,
    },
  );
  return requireData(unwrapApiData<MissionPublic>(res), '标记结束失败');
}

/** POST /api/v1/admin/missions/fission-data/list */
export async function fetchMissionFissionDataList(
  params: { mission_id: number; page?: number; page_size?: number },
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<MissionFissionDataPublic>>>(
    AdminMissionApi.FISSION_DATA_LIST,
    {
      method: 'POST',
      data: {
        mission_id: params.mission_id,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<MissionFissionDataPublic>>(res),
    '获取任务数据失败',
  );
}

/** POST /api/v1/admin/missions/fission-data/detail */
export async function fetchMissionFissionDataDetail(
  params: { id: number; mission_id: number; supplier_id?: number },
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<MissionFissionDataDetailPublic>>(
    AdminMissionApi.FISSION_DATA_DETAIL,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<MissionFissionDataDetailPublic>(res),
    '获取任务数据详情失败',
  );
}

/** POST /api/v1/admin/missions/fission-data/add */
export async function addMissionFissionData(
  params: MissionFissionDataAddParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<MissionFissionDataPublic>>(
    AdminMissionApi.FISSION_DATA_ADD,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<MissionFissionDataPublic>(res),
    '添加任务数据失败',
  );
}

/** POST /api/v1/admin/missions/fission-data/update */
export async function updateMissionFissionData(
  params: MissionFissionDataUpdateParams,
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<MissionFissionDataPublic>>(
    AdminMissionApi.FISSION_DATA_UPDATE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<MissionFissionDataPublic>(res),
    '更新任务数据失败',
  );
}

/** POST /api/v1/admin/missions/fission-data/delete */
export async function deleteMissionFissionData(
  params: { id: number; mission_id: number },
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<Record<string, never>>>(
    AdminMissionApi.FISSION_DATA_DELETE,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return unwrapApiData(res);
}

/** POST /api/v1/admin/missions/fission-data/mark-finished */
export async function markMissionFissionDataFinished(
  params: { id: number; mission_id: number },
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<MissionFissionDataPublic>>(
    AdminMissionApi.FISSION_DATA_MARK_FINISHED,
    {
      method: 'POST',
      data: params,
      ...options,
    },
  );
  return requireData(
    unwrapApiData<MissionFissionDataPublic>(res),
    '标记结束失败',
  );
}

/** POST /api/v1/admin/missions/logs/list */
export async function fetchMissionLogList(
  params: { mission_id: number; page?: number; page_size?: number },
  options?: RequestOptions,
) {
  const res = await request<ApiResponse<PageData<MissionLogPublic>>>(
    AdminMissionApi.LOGS_LIST,
    {
      method: 'POST',
      data: {
        mission_id: params.mission_id,
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
      },
      ...options,
    },
  );
  return requireData(
    unwrapApiData<PageData<MissionLogPublic>>(res),
    '获取执行日志失败',
  );
}

/** POST /api/v1/admin/missions/execute */
export async function executeMission(missionId: number, options?: RequestOptions) {
  const res = await request<
    ApiResponse<{
      mission_id: number;
      log_id: number;
      queued_count: number;
    }>
  >(AdminMissionApi.EXECUTE, {
    method: 'POST',
    data: { mission_id: missionId },
    ...options,
  });
  return requireData(unwrapApiData(res), '提交执行失败');
}
