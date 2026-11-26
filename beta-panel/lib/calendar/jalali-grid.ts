/**
 * Jalali (Persian) calendar navigation over Tehran wall-clock dates.
 *
 * All inputs/outputs are Gregorian `YYYY-MM-DD` strings in Asia/Tehran — the
 * API contract. Jalali values are derived with Intl (Latin digits) and only
 * used for presentation and navigation boundaries.
 */
import { tehranLocalToUtcIso, shiftTehranYmd } from "../tehran";

export const JALALI_MONTHS = [
  "فروردین",
  "اردیبهشت",
  "خرداد",
  "تیر",
  "مرداد",
  "شهریور",
  "مهر",
  "آبان",
  "آذر",
  "دی",
  "بهمن",
  "اسفند",
] as const;

/** Saturday-first week, as used in Iran. */
export const WEEKDAYS_SAT_FIRST = [
  "شنبه",
  "یکشنبه",
  "دوشنبه",
  "سه‌شنبه",
  "چهارشنبه",
  "پنجشنبه",
  "جمعه",
] as const;

export type JalaliParts = { jy: number; jm: number; jd: number };

const FORMATTER = new Intl.DateTimeFormat("en-US-u-ca-persian-nu-latn", {
  timeZone: "UTC",
  year: "numeric",
  month: "numeric",
  day: "numeric",
});

function utcNoon(ymd: string): Date {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12));
}

export function jalaliParts(ymd: string): JalaliParts {
  const parts = Object.fromEntries(
    FORMATTER.formatToParts(utcNoon(ymd)).map((part) => [part.type, part.value]),
  );
  return { jy: Number(parts.year), jm: Number(parts.month), jd: Number(parts.day) };
}

export function jalaliMonthStart(ymd: string): string {
  return shiftTehranYmd(ymd, -(jalaliParts(ymd).jd - 1));
}

export function jalaliMonthLength(ymd: string): number {
  const { jm } = jalaliParts(ymd);
  const start = jalaliMonthStart(ymd);
  for (let length = 29; length <= 31; length += 1) {
    if (jalaliParts(shiftTehranYmd(start, length)).jm !== jm) return length;
  }
  return 31;
}

export function shiftJalaliMonth(ymd: string, delta: number): string {
  let cursor = jalaliMonthStart(ymd);
  for (let i = 0; i < Math.abs(delta); i += 1) {
    cursor =
      delta > 0
        ? shiftTehranYmd(cursor, jalaliMonthLength(cursor))
        : jalaliMonthStart(shiftTehranYmd(cursor, -1));
  }
  return cursor;
}

/** Days since the preceding Saturday: Saturday=0 … Friday=6. */
export function weekdayIndexSatFirst(ymd: string): number {
  return (utcNoon(ymd).getUTCDay() + 1) % 7;
}

export function weekStart(ymd: string): string {
  return shiftTehranYmd(ymd, -weekdayIndexSatFirst(ymd));
}

export type CalendarView = "day" | "week" | "month";

export type VisibleRange = { startYmd: string; days: number };

/** Month view spans whole Saturday-first weeks (at most 42 days). */
export function visibleRange(view: CalendarView, ymd: string): VisibleRange {
  if (view === "day") return { startYmd: ymd, days: 1 };
  if (view === "week") return { startYmd: weekStart(ymd), days: 7 };
  const monthStart = jalaliMonthStart(ymd);
  const lead = weekdayIndexSatFirst(monthStart);
  const weeks = Math.ceil((lead + jalaliMonthLength(ymd)) / 7);
  return { startYmd: shiftTehranYmd(monthStart, -lead), days: weeks * 7 };
}

export function rangeBoundsUtc(range: VisibleRange): { start: string; end: string } {
  return {
    start: tehranLocalToUtcIso(`${range.startYmd}T00:00`),
    end: tehranLocalToUtcIso(`${shiftTehranYmd(range.startYmd, range.days)}T00:00`),
  };
}

export function stepView(view: CalendarView, ymd: string, direction: 1 | -1): string {
  if (view === "day") return shiftTehranYmd(ymd, direction);
  if (view === "week") return shiftTehranYmd(ymd, 7 * direction);
  return shiftJalaliMonth(ymd, direction);
}

export function formatJalaliMonthTitle(ymd: string): string {
  const { jy, jm } = jalaliParts(ymd);
  return `${JALALI_MONTHS[jm - 1]} ${jy}`;
}

export function formatRangeTitle(view: CalendarView, ymd: string): string {
  if (view === "month") return formatJalaliMonthTitle(ymd);
  const { startYmd, days } = visibleRange(view, ymd);
  const a = jalaliParts(startYmd);
  if (days === 1) return `${a.jd} ${JALALI_MONTHS[a.jm - 1]} ${a.jy}`;
  const b = jalaliParts(shiftTehranYmd(startYmd, days - 1));
  return `${a.jd} ${JALALI_MONTHS[a.jm - 1]} ${a.jy} تا ${b.jd} ${JALALI_MONTHS[b.jm - 1]} ${b.jy}`;
}

function compare(a: JalaliParts, b: JalaliParts): number {
  return a.jy - b.jy || a.jm - b.jm || a.jd - b.jd;
}

/** Gregorian Tehran date for a Jalali date; day is clamped into the month. */
export function fromJalali(jy: number, jm: number, jd: number): string {
  const guessMs = Date.UTC(jy + 621, 2, 21) + ((jm - 1) * 30.5 + (jd - 1)) * 86_400_000;
  const guess = new Date(guessMs);
  let ymd = `${guess.getUTCFullYear()}-${String(guess.getUTCMonth() + 1).padStart(2, "0")}-${String(guess.getUTCDate()).padStart(2, "0")}`;
  const target = { jy, jm, jd: 1 };
  for (let i = 0; i < 60; i += 1) {
    const order = compare(jalaliParts(ymd), target);
    if (order === 0 || (order > 0 && compare(jalaliParts(shiftTehranYmd(ymd, -1)), target) < 0)) break;
    ymd = shiftTehranYmd(ymd, order < 0 ? 1 : -1);
  }
  const start = jalaliMonthStart(ymd);
  const length = jalaliMonthLength(start);
  return shiftTehranYmd(start, Math.min(Math.max(jd, 1), length) - 1);
}
