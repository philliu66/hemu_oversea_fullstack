import { useEffect, useState } from 'react';
import { fetchDhMeasuresUnitList } from '@/services/common/utils';
import type { DhMeasuresUnitPublic } from '@/types/api';

let cache: DhMeasuresUnitPublic[] | null = null;
let pending: Promise<DhMeasuresUnitPublic[]> | null = null;

/** 计件单位列表（进程内缓存，供 Select request 与展示名解析共用） */
export async function loadMeasureUnits(): Promise<DhMeasuresUnitPublic[]> {
  if (cache) {
    return cache;
  }
  if (!pending) {
    pending = fetchDhMeasuresUnitList()
      .then((list) => {
        cache = list || [];
        return cache;
      })
      .catch((error) => {
        pending = null;
        throw error;
      });
  }
  return pending;
}

export function useMeasureUnits(): DhMeasuresUnitPublic[] {
  const [options, setOptions] = useState<DhMeasuresUnitPublic[]>(
    () => cache || [],
  );

  useEffect(() => {
    let cancelled = false;
    void loadMeasureUnits()
      .then((list) => {
        if (!cancelled) {
          setOptions(list);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOptions([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return options;
}
