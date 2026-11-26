"use client";

import { CSRF_COOKIE } from "./constants";
import { describeError } from "./error-messages";

export {
  formatTehran,
  tehranLocalToUtcIso,
  tehranTodayYmd,
  tehranDayBoundsUtc,
  shiftTehranYmd,
  tehranYmdOf,
  utcIsoToTehranLocal,
} from "./tehran";
export {
  bookingFingerprint,
  IdempotencyKeyStore,
  sortedConflictIds,
  type BookingIntent,
} from "./booking";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));
  if (!match) return null;
  return decodeURIComponent(match.slice(name.length + 1));
}

export async function ensureCsrf(): Promise<string> {
  let token = readCookie(CSRF_COOKIE);
  if (!token) {
    await fetch("/api/auth/csrf", { method: "GET", credentials: "same-origin" });
    token = readCookie(CSRF_COOKIE);
  }
  if (!token) {
    throw new Error("CSRF token unavailable");
  }
  return token;
}

export type ApiErrorBody = {
  error?: string;
  message?: string;
  detail?: unknown;
};

export type OverlapConflict = {
  appointment_id: string;
  display_safe_patient_name?: string;
  booking_channel?: string;
  scheduled_start_at_utc?: string;
  scheduled_end_at_utc?: string;
};

export function extractOverlapConflicts(data: ApiErrorBody): OverlapConflict[] | null {
  const detail = data.detail;
  if (!detail || typeof detail !== "object") {
    if (data.error === "manual_overlap_acknowledgement_required") {
      return [];
    }
    return null;
  }
  const d = detail as {
    error?: string;
    conflicts?: OverlapConflict[];
  };
  if (
    d.error === "manual_overlap_acknowledgement_required"
    || data.error === "manual_overlap_acknowledgement_required"
  ) {
    return Array.isArray(d.conflicts) ? d.conflicts : [];
  }
  return null;
}

export async function apiFetch(
  path: string,
  init: RequestInit & { csrf?: boolean } = {},
): Promise<Response> {
  const headers = new Headers(init.headers || {});
  if (init.csrf) {
    const csrf = await ensureCsrf();
    headers.set("x-csrf-token", csrf);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(path, {
    ...init,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
}

export function formatApiError(data: ApiErrorBody, fallback: string): string {
  const nested =
    typeof data.detail === "object" && data.detail && "message" in data.detail
      ? (data.detail as { message?: string }).message
      : undefined;
  return describeError(data.error, data.message ?? nested, fallback);
}
