"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
import type { AppointmentItem } from "./types";

type Props = {
  items: AppointmentItem[];
  onOpen?: ((item: AppointmentItem) => void) | null;
};

const DEFAULT_FIRST_HOUR = 8;
const DEFAULT_LAST_HOUR = 20;

function hourOf(item: AppointmentItem): number {
  return Number(formatTehranTime(item.scheduled_start_at_utc).slice(0, 2));
}

/** Working-hours grid that widens when an appointment falls outside it, so none is ever hidden. */
export function DayTimeline({ items, onOpen }: Props) {
  const hoursWithItems = items.map(hourOf);
  const first = Math.min(DEFAULT_FIRST_HOUR, ...hoursWithItems);
  const last = Math.max(DEFAULT_LAST_HOUR, ...hoursWithItems);
  const rows = Array.from({ length: last - first + 1 }, (_, index) => {
    const hour = first + index;
    return { hour, slots: items.filter((item) => hourOf(item) === hour) };
  });

  return (
    <section className="ds-card p-4" data-testid="appointments-timeline" aria-label="جدول زمانی روزانه">
      <h2 className="ds-section-title mb-3">جدول زمانی روز</h2>
      <ol className="divide-y divide-[var(--ds-border)]">
        {rows.map(({ hour, slots }) => (
          <li key={hour} className="grid grid-cols-[3.5rem_minmax(0,1fr)] items-start gap-3 py-2">
            <span className="pt-1 text-sm tabular-nums text-[var(--ds-text-muted)]">{String(hour).padStart(2, "0")}:00</span>
            <div className="flex min-h-8 flex-wrap gap-2">
              {slots.map((slot) => (
                <button
                  key={slot.appointment_id}
                  type="button"
                  disabled={!onOpen}
                  onClick={() => onOpen?.(slot)}
                  className="flex items-center gap-2 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] bg-[var(--ds-surface-muted)] px-2.5 py-1 text-xs hover:border-[var(--ds-primary)] disabled:cursor-default"
                >
                  <span className="tabular-nums font-medium">{formatTehranTime(slot.scheduled_start_at_utc)}</span>
                  <span>{slot.patient_first_name} {slot.patient_last_name}</span>
                  <StatusBadge tone={appointmentStatusTone(slot.status)}>{appointmentStatusLabel(slot.status)}</StatusBadge>
                </button>
              ))}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
