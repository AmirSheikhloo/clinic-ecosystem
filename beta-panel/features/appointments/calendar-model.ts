import { tehranYmdOf } from "../../lib/tehran";
import { shiftTehranYmd } from "../../lib/tehran";
import type { VisibleRange } from "../../lib/calendar/jalali-grid";
import type { AppointmentItem, SortKey } from "./types";

/** Buckets appointments by their Tehran calendar day, each bucket sorted by start time. */
export function groupByTehranDay<T extends AppointmentItem>(items: T[]): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const ymd = tehranYmdOf(item.scheduled_start_at_utc);
    const bucket = groups.get(ymd);
    if (bucket) bucket.push(item);
    else groups.set(ymd, [item]);
  }
  for (const bucket of groups.values()) {
    bucket.sort((a, b) => a.scheduled_start_at_utc.localeCompare(b.scheduled_start_at_utc));
  }
  return groups;
}

export function rangeDays(range: VisibleRange): string[] {
  return Array.from({ length: range.days }, (_, index) => shiftTehranYmd(range.startYmd, index));
}

export function sortAppointments<T extends AppointmentItem>(items: T[], key: SortKey): T[] {
  return items.slice().sort((a, b) => {
    if (key === "patient") {
      return `${a.patient_first_name}${a.patient_last_name}`.localeCompare(
        `${b.patient_first_name}${b.patient_last_name}`,
        "fa",
      );
    }
    if (key === "service") return a.service_name.localeCompare(b.service_name, "fa");
    return a.scheduled_start_at_utc.localeCompare(b.scheduled_start_at_utc);
  });
}

/** Minutes between two ISO instants, never below 1. */
export function durationMinutes(startIso: string, endIso: string): number {
  return Math.max(1, Math.round((Date.parse(endIso) - Date.parse(startIso)) / 60_000));
}

export function addMinutesIso(startIso: string, minutes: number): string {
  return new Date(Date.parse(startIso) + minutes * 60_000).toISOString();
}
