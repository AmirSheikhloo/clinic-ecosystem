"use client";

import { useCallback, useEffect, useState } from "react";
import { apiJson, type ApiFail, type ApiResult } from "./api";

export type QueryState<T> = {
  data: T | null;
  error: ApiFail | null;
  loading: boolean;
  reload: () => void;
};

/**
 * Fetches `path` (null disables). Superseded or unmounted requests are aborted,
 * and a single request is issued per (path, reload) change.
 */
export function useApiQuery<T>(
  path: string | null,
  fallbackMessage?: string,
  refreshKey = 0,
): QueryState<T> {
  const [token, setToken] = useState(0);
  const [settled, setSettled] = useState<{ key: string; result: ApiResult<T> } | null>(null);
  const key = path === null ? null : `${path}#${token}.${refreshKey}`;

  useEffect(() => {
    if (path === null || key === null) return;
    const controller = new AbortController();
    void apiJson<T>(path, { signal: controller.signal, fallbackMessage }).then((result) => {
      if (!controller.signal.aborted) setSettled({ key, result });
    });
    return () => controller.abort();
  }, [path, key, fallbackMessage]);

  const reload = useCallback(() => setToken((value) => value + 1), []);
  const current = settled && settled.key === key ? settled.result : null;
  return {
    data: current && current.ok ? current.data : null,
    error: current && !current.ok ? current : null,
    loading: key !== null && current === null,
    reload,
  };
}
