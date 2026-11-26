import type { ApiOk } from "./api";

/**
 * Opt-in response cache for slowly changing reference data (the service and resource catalog).
 * Entries expire after the caller's `cacheMs`, are keyed by request path, never hold patient or
 * account data, and are dropped by `invalidateQueryCache` after a related mutation and by
 * `clearQueryCache` on sign-out or session expiry.
 */
const entries = new Map<string, { at: number; result: ApiOk<unknown> }>();

export function readCached<T>(path: string | null, maxAgeMs: number | undefined): ApiOk<T> | null {
  if (!path || !maxAgeMs) return null;
  const hit = entries.get(path);
  return hit && Date.now() - hit.at < maxAgeMs ? (hit.result as ApiOk<T>) : null;
}

export function writeCached(path: string, result: ApiOk<unknown>): void {
  entries.set(path, { at: Date.now(), result });
}

export function invalidateQueryCache(pathPrefix?: string): void {
  for (const key of [...entries.keys()]) {
    if (!pathPrefix || key.startsWith(pathPrefix)) entries.delete(key);
  }
}

export function clearQueryCache(): void {
  entries.clear();
}

/** Reference-data freshness window; any catalog mutation invalidates earlier. */
export const CATALOG_CACHE_MS = 60_000;
