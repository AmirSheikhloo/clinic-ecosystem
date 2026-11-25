/**
 * Text parsing/formatting for the shared Jalali date and time controls.
 * Values exchanged with the API stay Gregorian `YYYY-MM-DD` / `YYYY-MM-DDTHH:mm` (Asia/Tehran wall clock).
 */
import { toLatinDigits } from "../format/digits";
import { shiftTehranYmd } from "../tehran";
import {
  fromJalali,
  jalaliMonthLength,
  jalaliMonthStart,
  jalaliParts,
  visibleRange,
} from "./jalali-grid";

export const JALALI_YEAR_MIN = 1300;
export const JALALI_YEAR_MAX = 1499;

const pad2 = (n: number) => String(n).padStart(2, "0");

/** `1405/09/04` — Latin digits, zero padded. */
export function formatJalaliInput(ymd: string): string {
  if (!ymd) return "";
  const { jy, jm, jd } = jalaliParts(ymd);
  return `${jy}/${pad2(jm)}/${pad2(jd)}`;
}

/**
 * Parse typed Jalali text (`1405/9/4`, `1405-09-04`, Persian digits accepted).
 * Returns the Gregorian Tehran date, or null when the text is not a real Jalali date.
 */
export function parseJalaliInput(text: string): string | null {
  const match = /^(\d{4})\D+(\d{1,2})\D+(\d{1,2})$/.exec(toLatinDigits(text).trim());
  if (!match) return null;
  const [jy, jm, jd] = [Number(match[1]), Number(match[2]), Number(match[3])];
  if (jy < JALALI_YEAR_MIN || jy > JALALI_YEAR_MAX || jm < 1 || jm > 12 || jd < 1) return null;
  const ymd = fromJalali(jy, jm, jd);
  const back = jalaliParts(ymd);
  return back.jy === jy && back.jm === jm && back.jd === jd ? ymd : null;
}

export type CalendarCell = { ymd: string; jd: number; inMonth: boolean };

/** Whole Saturday-first weeks covering the Jalali month of `ymd`. */
export function monthCells(ymd: string): CalendarCell[] {
  const { startYmd, days } = visibleRange("month", ymd);
  const month = jalaliParts(ymd).jm;
  return Array.from({ length: days }, (_, index) => {
    const cell = shiftTehranYmd(startYmd, index);
    const parts = jalaliParts(cell);
    return { ymd: cell, jd: parts.jd, inMonth: parts.jm === month };
  });
}

export function monthStartOf(ymd: string): string {
  return jalaliMonthStart(ymd);
}

export function clampToJalaliRange(ymd: string): string {
  const { jy } = jalaliParts(ymd);
  if (jy < JALALI_YEAR_MIN) return fromJalali(JALALI_YEAR_MIN, 1, 1);
  if (jy > JALALI_YEAR_MAX) return fromJalali(JALALI_YEAR_MAX, 12, jalaliMonthLength(fromJalali(JALALI_YEAR_MAX, 12, 1)));
  return ymd;
}

/** `HH:mm` from typed text; accepts `930`, `0930`, `9:30`, `09:30`, Persian digits. */
export function parseTimeInput(text: string): string | null {
  const latin = toLatinDigits(text).trim();
  const colon = /^(\d{1,2})[:.](\d{2})$/.exec(latin);
  const compact = /^(\d{3,4})$/.exec(latin);
  let hh: number;
  let mm: number;
  if (colon) {
    hh = Number(colon[1]);
    mm = Number(colon[2]);
  } else if (compact) {
    const digits = compact[1].padStart(4, "0");
    hh = Number(digits.slice(0, 2));
    mm = Number(digits.slice(2));
  } else {
    return null;
  }
  if (hh > 23 || mm > 59) return null;
  return `${pad2(hh)}:${pad2(mm)}`;
}

export function splitLocalDateTime(value: string): { date: string; time: string } {
  const [date = "", time = ""] = value.split("T");
  return { date, time: time.slice(0, 5) };
}

export function joinLocalDateTime(date: string, time: string): string {
  return date && time ? `${date}T${time}` : "";
}
