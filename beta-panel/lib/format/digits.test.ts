import assert from "node:assert/strict";
import { test } from "node:test";
import {
  containsNonLatinDigits,
  normalizeInputDigits,
  toLatinDigits,
} from "./digits";
import { formatCount } from "./numbers";
import { formatJalaliDateTime, formatJalaliFromTehranYmd } from "./jalali";
import { formatTehran, tehranDayBoundsUtc, tehranTodayYmd } from "../tehran";

test("toLatinDigits converts Persian and Arabic-Indic digits", () => {
  assert.equal(toLatinDigits("۱۴۰۳/۰۱/۰۲"), "1403/01/02");
  assert.equal(toLatinDigits("٢٠٢٤"), "2024");
  assert.equal(normalizeInputDigits("۱۲۳abc"), "123abc");
  assert.equal(containsNonLatinDigits("۱۲"), true);
  assert.equal(containsNonLatinDigits("12"), false);
});

test("formatCount uses Latin digits", () => {
  const value = formatCount(1234);
  assert.equal(containsNonLatinDigits(value), false);
  assert.match(value, /1/);
});

test("Jalali formatters never emit Persian/Arabic-Indic digits", () => {
  const iso = "2024-03-20T12:30:00.000Z";
  const dt = formatJalaliDateTime(iso);
  const viaTehran = formatTehran(iso);
  assert.equal(containsNonLatinDigits(dt), false);
  assert.equal(containsNonLatinDigits(viaTehran), false);
  assert.match(dt, /[0-9]/);
});

test("Tehran day bounds and today YMD stay Gregorian contract values", () => {
  const today = tehranTodayYmd(new Date("2024-08-01T10:00:00Z"));
  assert.match(today, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(containsNonLatinDigits(today), false);
  const bounds = tehranDayBoundsUtc(today);
  assert.ok(bounds.start.endsWith("Z") || bounds.start.includes("+") || bounds.start.includes("T"));
  assert.ok(Date.parse(bounds.end) > Date.parse(bounds.start));
  const label = formatJalaliFromTehranYmd(today);
  assert.equal(containsNonLatinDigits(label), false);
});
