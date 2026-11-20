/** Shared Asia/Tehran wall-clock helpers for reception UI. */

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

/** Inclusive Tehran day bounds as UTC ISO start (00:00) and exclusive end (next midnight). */
export function tehranDayBoundsUtc(dateYmd: string): { start: string; end: string } {
  const start = tehranLocalToUtcIso(`${dateYmd}T00:00`);
  const [y, m, d] = dateYmd.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + 1));
  const nextYmd = `${String(next.getUTCFullYear()).padStart(4, "0")}-${String(next.getUTCMonth() + 1).padStart(2, "0")}-${String(next.getUTCDate()).padStart(2, "0")}`;
  // Using calendar arithmetic on the YMD components keeps midnight boundaries stable.
  const end = tehranLocalToUtcIso(`${nextYmd}T00:00`);
  return { start, end };
}

export function formatTehran(isoUtc: string): string {
  return new Intl.DateTimeFormat("fa-IR", {
    timeZone: TEHRAN_TZ,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoUtc));
}
