import { useEffect, useState } from 'react';
import { fetchDhMeasuresUnitList } from '@/services/common/utils';
import type { DhMeasuresUnitPublic } from '@/types/api';

let cache: DhMeasuresUnitPublic[] | null = null;
let pending: Promise<DhMeasuresUnitPublic[]> | null = null;

type MeasureUnitsListener = (list: DhMeasuresUnitPublic[]) => void;
const listeners = new Set<MeasureUnitsListener>();

function notifyMeasureUnits(list: DhMeasuresUnitPublic[]) {
  listeners.forEach((listener) => listener(list));
}

/** 计件单位列表（进程内缓存，供 Select 与展示名解析共用） */
export async function loadMeasureUnits(): Promise<DhMeasuresUnitPublic[]> {
  if (cache !== null) {
    return cache;
  }
  if (!pending) {
    pending = fetchDhMeasuresUnitList()
      .then((list) => {
        cache = list || [];
        notifyMeasureUnits(cache);
        return cache;
      })
      .catch((error) => {
        pending = null;
        throw error;
      });
  }
  return pending;
}

export function useMeasureUnits(): {
  options: DhMeasuresUnitPublic[];
  loading: boolean;
} {
  const [options, setOptions] = useState<DhMeasuresUnitPublic[]>(
    () => cache || [],
  );
  const [loading, setLoading] = useState(() => cache === null);

  useEffect(() => {
    let cancelled = false;
    const onUpdate: MeasureUnitsListener = (list) => {
      if (!cancelled) {
        setOptions(list);
        setLoading(false);
      }
    };
    listeners.add(onUpdate);
    if (cache !== null) {
      setOptions(cache);
      setLoading(false);
    } else {
      setLoading(true);
      void loadMeasureUnits().catch(() => {
        if (!cancelled) {
          setOptions([]);
          setLoading(false);
        }
      });
    }
    return () => {
      cancelled = true;
      listeners.delete(onUpdate);
    };
  }, []);

  return { options, loading };
}
