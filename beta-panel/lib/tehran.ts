/** Shared Asia/Tehran wall-clock helpers for reception UI. */

import { formatJalaliDateTime } from "./format/jalali";

export const TEHRAN_TZ = "Asia/Tehran";

function tehranParts(date: Date): Record<string, string> {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: TEHRAN_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  return Object.fromEntries(
    formatter.formatToParts(date).map((part) => [part.type, part.value]),
  );
}

/** Convert datetime-local string (Tehran wall clock) to UTC ISO. */
export function tehranLocalToUtcIso(localValue: string): string {
  const [datePart, timePart] = localValue.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm] = (timePart || "00:00").split(":").map(Number);
  const guess = new Date(Date.UTC(y, m - 1, d, hh, mm, 0));
  const parts = tehranParts(guess);
  const asTehran = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour) % 24,
    Number(parts.minute),
    Number(parts.second),
  );
  return new Date(guess.getTime() - (asTehran - guess.getTime())).toISOString();
}

/** Today's calendar date in Tehran as YYYY-MM-DD. */
export function tehranTodayYmd(now: Date = new Date()): string {
  const parts = tehranParts(now);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/** Current Tehran wall clock as `YYYY-MM-DDTHH:mm` for datetime-local fields. */
export function tehranNowLocalInput(now: Date = new Date()): string {
  return utcIsoToTehranLocal(now.toISOString());
}

/** UTC instant -> `YYYY-MM-DDTHH:mm` Tehran wall clock, the inverse of tehranLocalToUtcIso. */
export function utcIsoToTehranLocal(isoUtc: string): string {
  const parts = tehranParts(new Date(isoUtc));
  return `${parts.year}-${parts.month}-${parts.day}T${String(Number(parts.hour) % 24).padStart(2, "0")}:${parts.minute}`;
}

/** Tehran calendar date (YYYY-MM-DD) of a UTC instant. */
export function tehranYmdOf(isoUtc: string): string {
  const parts = tehranParts(new Date(isoUtc));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/** Shift a Tehran YMD by ±days using Gregorian calendar arithmetic (UTC noon anchor). */
export function shiftTehranYmd(ymd: string, deltaDays: number): string {
  const [y, m, d] = ymd.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + deltaDays));
  return `${String(next.getUTCFullYear()).padStart(4, "0")}-${String(next.getUTCMonth() + 1).padStart(2, "0")}-${String(next.getUTCDate()).padStart(2, "0")}`;
}

/** Inclusive Tehran day bounds as UTC ISO start (00:00) and exclusive end (next midnight). */
export function tehranDayBoundsUtc(dateYmd: string): { start: string; end: string } {
  const start = tehranLocalToUtcIso(`${dateYmd}T00:00`);
  const nextYmd = shiftTehranYmd(dateYmd, 1);
  const end = tehranLocalToUtcIso(`${nextYmd}T00:00`);
  return { start, end };
}

/** Compact 24h Tehran clock `HH:mm`. */
export function formatTehranClock(now: Date = new Date()): string {
  const parts = tehranParts(now);
  return `${String(Number(parts.hour) % 24).padStart(2, "0")}:${parts.minute}`;
}

/** Compact Jalali date label for the top bar (Latin digits). */
export function tehranTodayJalaliLabel(now: Date = new Date()): string {
  return formatJalaliDateTime(now.toISOString()).split(" ")[0] || formatJalaliDateTime(now.toISOString());
}

/**
 * Display helper: Jalali calendar in Asia/Tehran with Latin digits 0–9.
 * API/DB contracts remain Gregorian/UTC; this is presentation only.
 */
export function formatTehran(isoUtc: string): string {
  return formatJalaliDateTime(isoUtc);
}
