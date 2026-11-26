import assert from "node:assert/strict";
import test from "node:test";
import { containsNonLatinDigits } from "../format/digits.ts";
import {
  formatJalaliInput,
  joinLocalDateTime,
  monthCells,
  parseJalaliInput,
  parseTimeInput,
  splitLocalDateTime,
} from "./jalali-input.ts";

test("format and parse round-trip Jalali dates with Latin digits", () => {
  assert.equal(formatJalaliInput("2025-03-21"), "1404/01/01");
  assert.equal(parseJalaliInput("1404/01/01"), "2025-03-21");
  assert.equal(parseJalaliInput("1404-1-1"), "2025-03-21");
  assert.equal(formatJalaliInput("2026-11-25"), "1405/09/04");
  assert.equal(parseJalaliInput(formatJalaliInput("2026-11-25")), "2026-11-25");
  assert.equal(containsNonLatinDigits(formatJalaliInput("2026-11-25")), false);
});

test("Persian and Arabic-Indic digits are accepted as input only", () => {
  assert.equal(parseJalaliInput("۱۴۰۵/۰۹/۰۴"), "2026-11-25");
  assert.equal(parseJalaliInput("١٤٠٥/٠٩/٠٤"), "2026-11-25");
});

test("invalid or non-existent Jalali dates are rejected", () => {
  assert.equal(parseJalaliInput(""), null);
  assert.equal(parseJalaliInput("1405/13/01"), null);
  assert.equal(parseJalaliInput("1405/07/31"), null, "Mehr has 30 days");
  assert.equal(parseJalaliInput("1404/12/30"), null, "Esfand 1404 is a 29-day month");
  assert.equal(parseJalaliInput("1403/12/30"), "2025-03-20", "Esfand 1403 is leap");
  assert.equal(parseJalaliInput("99/01/01"), null);
  assert.equal(parseJalaliInput("1405/09"), null);
});

test("month cells are whole Saturday-first weeks and flag the month", () => {
  const cells = monthCells("2026-11-25");
  assert.equal(cells.length % 7, 0);
  assert.ok(cells.length <= 42);
  assert.equal(cells.filter((c) => c.inMonth).length, 30, "Azar has 30 days");
  assert.equal(cells.find((c) => c.inMonth)?.jd, 1);
  assert.ok(cells.every((c) => c.jd >= 1 && c.jd <= 31));
});

test("time parsing accepts compact and colon forms and rejects out-of-range values", () => {
  assert.equal(parseTimeInput("0930"), "09:30");
  assert.equal(parseTimeInput("930"), "09:30");
  assert.equal(parseTimeInput("9:30"), "09:30");
  assert.equal(parseTimeInput("۱۴:۳۰"), "14:30");
  assert.equal(parseTimeInput("24:00"), null);
  assert.equal(parseTimeInput("12:60"), null);
  assert.equal(parseTimeInput("abc"), null);
});

test("local datetime helpers keep the datetime-local contract", () => {
  assert.deepEqual(splitLocalDateTime("2026-11-25T14:30"), { date: "2026-11-25", time: "14:30" });
  assert.equal(joinLocalDateTime("2026-11-25", "14:30"), "2026-11-25T14:30");
  assert.equal(joinLocalDateTime("2026-11-25", ""), "");
  assert.deepEqual(splitLocalDateTime(""), { date: "", time: "" });
});
