"use client";

import { CSRF_COOKIE } from "./constants";

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
  if (data.message) return data.message;
  if (data.error) return data.error;
  return fallback;
}

/** Convert a local datetime-local value (Asia/Tehran wall clock) to ISO UTC. */
export function tehranLocalToUtcIso(localValue: string): string {
  // localValue: YYYY-MM-DDTHH:mm from datetime-local input, interpreted as Asia/Tehran.
  const [datePart, timePart] = localValue.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm] = timePart.split(":").map(Number);
  // Build a UTC guess then adjust using Asia/Tehran offset at that instant.
  const guess = new Date(Date.UTC(y, m - 1, d, hh, mm, 0));
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tehran",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(
    formatter.formatToParts(guess).map((p) => [p.type, p.value]),
  );
  const asTehran = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour) % 24,
    Number(parts.minute),
    Number(parts.second),
  );
  const offsetMs = asTehran - guess.getTime();
  return new Date(guess.getTime() - offsetMs).toISOString();
}

export function formatTehran(isoUtc: string): string {
  const dt = new Date(isoUtc);
  return new Intl.DateTimeFormat("fa-IR", {
    timeZone: "Asia/Tehran",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(dt);
}
