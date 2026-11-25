"use client";

import { useCallback, useEffect, useState } from "react";
import { apiJson, type ApiFail, type ApiResult } from "./api";

export type QueryState<T> = {
  /** Data for the current request context; null while nothing usable exists. */
  data: T | null;
  error: ApiFail | null;
  /** First load for this context: no data to show yet. */
  loading: boolean;
  /** A request is in flight while earlier data stays on screen (explicit reload or kept results). */
  refreshing: boolean;
  /** The data on screen belongs to an earlier path (only with `keepPrevious`). */
  stale: boolean;
  reload: () => void;
};

export type QueryOptions = {
  /**
   * Keep the previous path's results visible (flagged `stale`) while a new path loads. Only for
   * list filters/paging of one resource; never for identity-scoped data such as a single patient.
   */
  keepPrevious?: boolean;
};

type Settled<T> = { path: string; key: string; result: ApiResult<T> };

/**
 * Fetches `path` (null disables). Cache lifetime is the component lifetime: nothing is shared across
 * mounts, so logout, tenant switches and authorization failures never leak earlier data.
 *  - same path + explicit reload/refreshKey: previous data stays (stale-while-revalidate);
 *  - different path: data is cleared unless `keepPrevious` is set;
 *  - superseded or unmounted requests are aborted and their results discarded.
 */
export function useApiQuery<T>(
  path: string | null,
  fallbackMessage?: string,
  refreshKey = 0,
  options: QueryOptions = {},
): QueryState<T> {
  const [token, setToken] = useState(0);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const key = path === null ? null : `${path}#${token}.${refreshKey}`;

  useEffect(() => {
    if (path === null || key === null) return;
    const controller = new AbortController();
    void apiJson<T>(path, { signal: controller.signal, fallbackMessage }).then((result) => {
      if (!controller.signal.aborted) setSettled({ path, key, result });
    });
    return () => controller.abort();
  }, [path, key, fallbackMessage]);

  const reload = useCallback(() => setToken((value) => value + 1), []);

  const fresh = settled !== null && settled.key === key;
  const usable = settled !== null && key !== null && (settled.result.ok || fresh);
  const sameContext = settled !== null && settled.path === path;
  const shown = usable && (sameContext || options.keepPrevious) ? settled : null;
  const result = shown?.result ?? null;

  return {
    data: result && result.ok ? result.data : null,
    error: result && !result.ok ? result : null,
    loading: key !== null && shown === null,
    refreshing: key !== null && shown !== null && !fresh,
    stale: shown !== null && shown.path !== path,
    reload,
  };
}
