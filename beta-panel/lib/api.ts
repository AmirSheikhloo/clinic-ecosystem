"use client";

import { apiFetch, type ApiErrorBody } from "./client";

export const SESSION_EXPIRED_EVENT = "ce:session-expired";

export type ApiOk<T> = {
  ok: true;
  status: number;
  data: T;
  etag: string | null;
  replayed: boolean;
};

export type ApiFail = {
  ok: false;
  status: number;
  error: string;
  message: string;
  body: ApiErrorBody;
  aborted: boolean;
  currentVersion: number | null;
};

export type ApiResult<T> = ApiOk<T> | ApiFail;

export type ApiJsonOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Sent as If-Match for expected-version updates. */
  version?: number | string;
  idempotencyKey?: string;
  signal?: AbortSignal;
  fallbackMessage?: string;
};

export function messageFromBody(body: ApiErrorBody, fallback: string): string {
  if (body.message) return body.message;
  if (typeof body.detail === "object" && body.detail && "message" in body.detail) {
    const message = (body.detail as { message?: string }).message;
    if (message) return message;
  }
  return fallback;
}

function currentVersionOf(body: ApiErrorBody): number | null {
  const detail = body.detail;
  if (detail && typeof detail === "object" && "current_version" in detail) {
    const value = (detail as { current_version?: unknown }).current_version;
    if (typeof value === "number") return value;
  }
  return null;
}

/** Typed JSON call against the BFF with CSRF, If-Match and Idempotency-Key handling. */
export async function apiJson<T>(path: string, options: ApiJsonOptions = {}): Promise<ApiResult<T>> {
  const method = options.method ?? "GET";
  const mutating = method !== "GET";
  const headers: Record<string, string> = {};
  if (options.version !== undefined) headers["If-Match"] = `"${options.version}"`;
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;
  try {
    const response = await apiFetch(path, {
      method,
      headers,
      csrf: mutating,
      signal: options.signal,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    const body = (response.status === 204
      ? {}
      : await response.json().catch(() => ({}))) as ApiErrorBody;
    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        error: body.error ?? "request_failed",
        message: messageFromBody(body, options.fallbackMessage ?? "درخواست ناموفق بود"),
        body,
        aborted: false,
        currentVersion: currentVersionOf(body),
      };
    }
    return {
      ok: true,
      status: response.status,
      data: body as T,
      etag: response.headers.get("etag"),
      replayed: response.headers.get("idempotent-replay") === "true",
    };
  } catch (err) {
    const aborted = err instanceof DOMException && err.name === "AbortError";
    return {
      ok: false,
      status: 0,
      error: aborted ? "aborted" : "network_error",
      message: aborted ? "درخواست لغو شد" : "ارتباط با سرور برقرار نشد",
      body: {},
      aborted,
      currentVersion: null,
    };
  }
}

/** Builds a query string, skipping empty values. */
export function buildQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
