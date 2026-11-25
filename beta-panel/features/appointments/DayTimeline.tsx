"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
import { layoutDay, minutesOfDay } from "./day-layout";
import type { AppointmentItem } from "./types";

type Props = {
  items: AppointmentItem[];
  onOpen?: ((item: AppointmentItem) => void) | null;
};

const DEFAULT_FIRST_HOUR = 8;
const DEFAULT_LAST_HOUR = 20;

/**
 * Proportional day schedule. The hour range widens when an appointment falls outside working hours,
 * overlapping visits share the row side by side, and a dense day scrolls inside its own frame.
 */
export function DayTimeline({ items, onOpen }: Props) {
  const placements = layoutDay(items);
  const startHours = items.map((item) => Math.floor(minutesOfDay(item.scheduled_start_at_utc) / 60));
  const endHours = Array.from(placements.values()).map((place) => Math.ceil(place.endMinutes / 60) - 1);
  const first = Math.min(DEFAULT_FIRST_HOUR, ...startHours);
  const last = Math.min(23, Math.max(DEFAULT_LAST_HOUR, ...startHours, ...endHours));
  const hours = Array.from({ length: last - first + 1 }, (_, index) => first + index);

  return (
    <section className="ds-card p-4" data-testid="appointments-timeline" aria-label="جدول زمانی روزانه">
      <h2 className="ds-section-title mb-3">جدول زمانی روز</h2>
      <div className="ds-day-scroll" tabIndex={0} aria-label="جدول زمانی؛ برای پیمایش از کلیدهای جهت‌نما استفاده کنید">
        <div className="ds-day-grid" style={{ "--ds-hours": hours.length } as React.CSSProperties}>
          <ol className="ds-day-hours" aria-hidden="true">
            {hours.map((hour) => (
              <li key={hour}>{String(hour).padStart(2, "0")}:00</li>
            ))}
          </ol>
          <div className="ds-day-track">
            {hours.map((hour) => (
              <div key={hour} className="ds-day-line" />
            ))}
            {items.map((item) => {
              const place = placements.get(item.appointment_id)!;
              const top = ((place.startMinutes - first * 60) / 60) * 100;
              const height = ((place.endMinutes - place.startMinutes) / 60) * 100;
              const compact = place.endMinutes - place.startMinutes < 45;
              const label = `${item.patient_first_name} ${item.patient_last_name}`;
              return (
                <button
                  key={item.appointment_id}
                  type="button"
                  disabled={!onOpen}
                  onClick={() => onOpen?.(item)}
                  className="ds-day-event"
                  data-tone={appointmentStatusTone(item.status)}
                  data-testid="timeline-event"
                  aria-label={`${formatTehranTime(item.scheduled_start_at_utc)} ${label}، ${item.service_name}، ${appointmentStatusLabel(item.status)}`}
                  title={`${label} — ${item.service_name}`}
                  style={{
                    insetBlockStart: `calc(var(--ds-hour-height) * ${top / 100})`,
                    height: `calc(var(--ds-hour-height) * ${height / 100} - 2px)`,
                    insetInlineStart: `${(place.lane / place.lanes) * 100}%`,
                    width: `calc(${100 / place.lanes}% - 4px)`,
                  }}
                >
                  <span className="flex min-w-0 gap-1.5">
                    <span className="flex-none tabular-nums font-medium">{formatTehranTime(item.scheduled_start_at_utc)}</span>
                    <span className="truncate">{label}</span>
                  </span>
                  {compact ? null : (
                    <>
                      <span className="ds-day-event-service truncate">{item.service_name}</span>
                      <StatusBadge tone={appointmentStatusTone(item.status)}>{appointmentStatusLabel(item.status)}</StatusBadge>
                    </>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
