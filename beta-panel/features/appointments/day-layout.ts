import { formatTehranTime } from "../../lib/format/jalali";
import type { AppointmentItem } from "./types";

/** Visual minimum so a very short visit stays clickable and overlap is judged on what is drawn. */
export const MIN_VISUAL_MINUTES = 30;

export type Placement = { lane: number; lanes: number; startMinutes: number; endMinutes: number };

export function minutesOfDay(isoUtc: string): number {
  const [hours, minutes] = formatTehranTime(isoUtc).split(":").map(Number);
  return hours * 60 + minutes;
}

/**
 * Places each appointment in a lane within its overlap cluster, so simultaneous visits sit side by
 * side instead of on top of each other. Visits that cross midnight are clamped to the day's end.
 */
export function layoutDay(items: AppointmentItem[]): Map<string, Placement> {
  const prepared = items
    .map((item) => {
      const startMinutes = minutesOfDay(item.scheduled_start_at_utc);
      const duration = Math.max(
        MIN_VISUAL_MINUTES,
        Math.round((Date.parse(item.scheduled_end_at_utc) - Date.parse(item.scheduled_start_at_utc)) / 60_000),
      );
      return { id: item.appointment_id, startMinutes, endMinutes: Math.min(startMinutes + duration, 24 * 60) };
    })
    .sort((a, b) => a.startMinutes - b.startMinutes || a.endMinutes - b.endMinutes || a.id.localeCompare(b.id));

  const result = new Map<string, Placement>();
  let cluster: { id: string; lane: number }[] = [];
  let laneEnds: number[] = [];
  let clusterEnd = -1;

  const flush = () => {
    for (const member of cluster) {
      const placed = result.get(member.id)!;
      result.set(member.id, { ...placed, lanes: laneEnds.length });
    }
    cluster = [];
    laneEnds = [];
  };

  for (const entry of prepared) {
    if (entry.startMinutes >= clusterEnd && cluster.length) flush();
    let lane = laneEnds.findIndex((end) => end <= entry.startMinutes);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(entry.endMinutes);
    } else {
      laneEnds[lane] = entry.endMinutes;
    }
    clusterEnd = cluster.length ? Math.max(clusterEnd, entry.endMinutes) : entry.endMinutes;
    cluster.push({ id: entry.id, lane });
    result.set(entry.id, { lane, lanes: 1, startMinutes: entry.startMinutes, endMinutes: entry.endMinutes });
  }
  flush();
  return result;
}
