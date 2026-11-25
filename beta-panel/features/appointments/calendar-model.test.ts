import assert from "node:assert/strict";
import test from "node:test";
import { addMinutesIso, durationMinutes, groupByTehranDay, rangeDays, sortAppointments } from "./calendar-model.ts";
import { visibleRange } from "../../lib/calendar/jalali-grid.ts";
import { tehranLocalToUtcIso, utcIsoToTehranLocal } from "../../lib/tehran.ts";
import type { AppointmentItem } from "./types.ts";

function item(id: string, startLocal: string, patient = "الف"): AppointmentItem {
  const start = tehranLocalToUtcIso(startLocal);
  return {
    appointment_id: id,
    patient_first_name: patient,
    patient_last_name: "ب",
    service_name: "S",
    status: "CONFIRMED",
    scheduled_start_at_utc: start,
    scheduled_end_at_utc: addMinutesIso(start, 30),
  };
}

test("groupByTehranDay uses the Tehran day, not the UTC day", () => {
  const late = item("late", "2025-03-22T23:45");
  const early = item("early", "2025-03-23T00:15");
  assert.ok(late.scheduled_start_at_utc.startsWith("2025-03-22T20"));
  const groups = groupByTehranDay([early, late, item("morning", "2025-03-22T09:00")]);
  assert.deepEqual(Array.from(groups.keys()).sort(), ["2025-03-22", "2025-03-23"]);
  assert.deepEqual(groups.get("2025-03-22")!.map((i) => i.appointment_id), ["morning", "late"]);
});

test("rangeDays enumerates the visible range", () => {
  const days = rangeDays(visibleRange("week", "2025-03-26"));
  assert.equal(days.length, 7);
  assert.equal(days[0], "2025-03-22");
  assert.equal(days[6], "2025-03-28");
});

test("sortAppointments is stable per key and does not mutate input", () => {
  const input = [item("b", "2025-03-22T10:00", "ز"), item("a", "2025-03-22T09:00", "الف")];
  const byTime = sortAppointments(input, "time");
  assert.deepEqual(byTime.map((i) => i.appointment_id), ["a", "b"]);
  assert.deepEqual(input.map((i) => i.appointment_id), ["b", "a"]);
  assert.deepEqual(sortAppointments(input, "patient").map((i) => i.appointment_id), ["a", "b"]);
});

test("duration and Tehran local round trip", () => {
  const start = tehranLocalToUtcIso("2025-03-22T09:30");
  assert.equal(utcIsoToTehranLocal(start), "2025-03-22T09:30");
  assert.equal(durationMinutes(start, addMinutesIso(start, 45)), 45);
  assert.equal(durationMinutes(start, start), 1);
});
