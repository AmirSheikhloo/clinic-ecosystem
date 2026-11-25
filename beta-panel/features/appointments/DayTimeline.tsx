"use client";

import { Card } from "@/components/ui/Card";
import { formatTehranTime } from "@/lib/format/jalali";
import type { AppointmentItem } from "./types";

type Props = {
  items: AppointmentItem[];
};

export function DayTimeline({ items }: Props) {
  const hours: { hour: number; slots: AppointmentItem[] }[] = [];
  for (let hour = 8; hour <= 20; hour += 1) {
    hours.push({
      hour,
      slots: items.filter((item) => {
        const local = formatTehranTime(item.scheduled_start_at_utc);
        const hh = Number(local.slice(0, 2));
        return hh === hour;
      }),
    });
  }

  return (
    <Card data-testid="appointments-timeline">
      <h3 className="mb-3 font-semibold">جدول زمانی روزانه</h3>
      <div className="space-y-2">
        {hours.map(({ hour, slots }) => (
          <div
            key={hour}
            className="grid grid-cols-[4rem_1fr] gap-3 border-b border-[var(--ds-border)] py-2 last:border-0"
          >
            <div className="tabular-nums text-sm text-[var(--ds-text-muted)]">
              {String(hour).padStart(2, "0")}:00
            </div>
            <div className="flex flex-wrap gap-2">
              {!slots.length && (
                <span className="text-xs text-[var(--ds-text-muted)]">—</span>
              )}
              {slots.map((slot) => (
                <span
                  key={slot.appointment_id}
                  className="rounded-md bg-[var(--ds-surface-muted)] px-2 py-1 text-xs tabular-nums"
                >
                  {formatTehranTime(slot.scheduled_start_at_utc)} · {slot.patient_first_name}{" "}
                  {slot.patient_last_name}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
