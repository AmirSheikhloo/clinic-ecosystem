import assert from "node:assert/strict";
import test from "node:test";
import {
  formatJalaliMonthTitle,
  formatRangeTitle,
  fromJalali,
  jalaliMonthLength,
  jalaliMonthStart,
  jalaliParts,
  rangeBoundsUtc,
  shiftJalaliMonth,
  stepView,
  visibleRange,
  weekStart,
  weekdayIndexSatFirst,
} from "./jalali-grid.ts";

test("jalaliParts matches known anchors with Latin digits", () => {
  assert.deepEqual(jalaliParts("2025-03-21"), { jy: 1404, jm: 1, jd: 1 });
  assert.deepEqual(jalaliParts("2024-03-20"), { jy: 1403, jm: 1, jd: 1 });
  assert.deepEqual(jalaliParts("2026-01-01"), { jy: 1404, jm: 10, jd: 11 });
});

test("month boundaries and lengths follow the Jalali calendar", () => {
  assert.equal(jalaliMonthStart("2025-04-10"), "2025-03-21");
  assert.equal(jalaliMonthLength("2025-04-10"), 31);
  assert.equal(jalaliMonthLength("2025-10-10"), 30);
  assert.equal(jalaliMonthLength("2025-03-01"), 30, "Esfand 1403 is a leap-year month");
  assert.equal(jalaliMonthLength("2026-03-01"), 29, "Esfand 1404 is a common-year month");
});

test("shiftJalaliMonth moves across year ends in both directions", () => {
  assert.equal(shiftJalaliMonth("2025-03-21", 1), "2025-04-21");
  assert.equal(shiftJalaliMonth("2025-03-21", -1), "2025-02-19");
  assert.equal(shiftJalaliMonth("2025-03-10", 12), "2026-02-20");
  assert.equal(shiftJalaliMonth("2025-04-05", 0), "2025-03-21");
});

test("weeks start on Saturday", () => {
  assert.equal(weekdayIndexSatFirst("2025-03-22"), 0);
  assert.equal(weekdayIndexSatFirst("2025-03-28"), 6);
  assert.equal(weekStart("2025-03-26"), "2025-03-22");
  assert.equal(weekStart("2025-03-22"), "2025-03-22");
});

test("visibleRange never exceeds the 42-day API limit and covers the month", () => {
  for (let m = 0; m < 24; m += 1) {
    const anchor = shiftJalaliMonth("2024-03-20", m);
    const range = visibleRange("month", anchor);
    assert.ok(range.days % 7 === 0 && range.days >= 28 && range.days <= 42, `days=${range.days}`);
    assert.equal(weekdayIndexSatFirst(range.startYmd), 0);
    const last = jalaliMonthLength(anchor);
    const monthEnd = new Date(`${jalaliMonthStart(anchor)}T12:00:00Z`).getTime() + (last - 1) * 86_400_000;
    const rangeEnd = new Date(`${range.startYmd}T12:00:00Z`).getTime() + (range.days - 1) * 86_400_000;
    assert.ok(rangeEnd >= monthEnd);
  }
  assert.deepEqual(visibleRange("day", "2025-03-21"), { startYmd: "2025-03-21", days: 1 });
  assert.deepEqual(visibleRange("week", "2025-03-26"), { startYmd: "2025-03-22", days: 7 });
});

test("rangeBoundsUtc uses Tehran midnights", () => {
  const { start, end } = rangeBoundsUtc({ startYmd: "2025-03-22", days: 2 });
  assert.equal(start, "2025-03-21T20:30:00.000Z");
  assert.equal(end, "2025-03-23T20:30:00.000Z");
});

test("stepView and titles use Persian month names and Latin digits", () => {
  assert.equal(stepView("day", "2025-03-21", 1), "2025-03-22");
  assert.equal(stepView("week", "2025-03-21", -1), "2025-03-14");
  assert.equal(stepView("month", "2025-03-21", 1), "2025-04-21");
  assert.equal(formatJalaliMonthTitle("2025-03-21"), "فروردین 1404");
  assert.equal(formatRangeTitle("day", "2025-03-21"), "1 فروردین 1404");
  assert.match(formatRangeTitle("week", "2025-03-26"), /^\d+ \S+ 1404 تا \d+ \S+ 1404$/);
  assert.doesNotMatch(formatRangeTitle("month", "2025-03-21"), /[۰-۹٠-٩]/);
});

test("fromJalali round-trips and clamps the day", () => {
  assert.equal(fromJalali(1404, 1, 1), "2025-03-21");
  assert.equal(fromJalali(1404, 12, 29), "2026-03-20");
  assert.equal(fromJalali(1404, 12, 31), "2026-03-20");
  assert.equal(fromJalali(1403, 12, 30), "2025-03-20");
  for (const ymd of ["2025-06-15", "2026-01-01", "2026-03-20", "2026-03-21"]) {
    const { jy, jm, jd } = jalaliParts(ymd);
    assert.equal(fromJalali(jy, jm, jd), ymd);
  }
});
