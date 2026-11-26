import { toLatinDigits } from "./digits";

/** Keep timezone constant local to avoid circular import with tehran.ts. */
const TEHRAN_TZ = "Asia/Tehran";

const JALALI_LATN: Intl.DateTimeFormatOptions = {
  timeZone: TEHRAN_TZ,
  calendar: "persian",
  numberingSystem: "latn",
};

/** Format UTC ISO as Jalali date+time in Tehran with Latin digits. */
export function formatJalaliDateTime(isoUtc: string): string {
  const formatted = new Intl.DateTimeFormat("fa-IR", {
    ...JALALI_LATN,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoUtc));
  return toLatinDigits(formatted);
}

/** Format UTC ISO as Jalali date only (Latin digits). */
export function formatJalaliDate(isoUtc: string): string {
  const formatted = new Intl.DateTimeFormat("fa-IR", {
    ...JALALI_LATN,
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(isoUtc));
  return toLatinDigits(formatted);
}

/** Format Tehran YMD (Gregorian wall date) as Jalali label with Latin digits. */
export function formatJalaliFromTehranYmd(ymd: string): string {
  const [y, m, d] = ymd.split("-").map(Number);
  // Anchor near Tehran midday without importing tehran.ts (avoids circular deps).
  const utcMs = Date.UTC(y, m - 1, d, 9, 0, 0);
  return formatJalaliDate(new Date(utcMs).toISOString());
}

/** Time-only in Tehran with Latin digits. */
export function formatTehranTime(isoUtc: string): string {
  const formatted = new Intl.DateTimeFormat("fa-IR", {
    timeZone: TEHRAN_TZ,
    numberingSystem: "latn",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(isoUtc));
  return toLatinDigits(formatted);
}
