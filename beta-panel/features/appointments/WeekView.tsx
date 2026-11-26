import { EmptyState } from "@/components/feedback/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { WEEKDAYS_SAT_FIRST, jalaliParts, JALALI_MONTHS } from "@/lib/calendar/jalali-grid";
import { formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
import type { CalendarItem } from "./types";

type Props = {
  days: string[];
  groups: Map<string, CalendarItem[]>;
  todayYmd: string;
  onOpen: ((item: CalendarItem) => void) | null;
};

export function WeekView({ days, groups, todayYmd, onOpen }: Props) {
  const total = Array.from(groups.values()).reduce((sum, list) => sum + list.length, 0);
  if (total === 0) return <EmptyState title="نوبتی برای این هفته ثبت نشده است" />;
  return (
    <div className="ds-week-scroll" data-testid="week-view">
      <div className="ds-week-grid">
        {days.map((ymd, index) => {
          const { jd, jm } = jalaliParts(ymd);
          const items = groups.get(ymd) ?? [];
          return (
            <section
              key={ymd}
              aria-label={`${WEEKDAYS_SAT_FIRST[index]} ${jd} ${JALALI_MONTHS[jm - 1]}`}
              className={`ds-card ds-week-day space-y-2 p-3 ${ymd === todayYmd ? "ring-2 ring-[var(--ds-primary)]" : ""}`}
              data-testid="week-day"
            >
              <h4 className="text-sm font-semibold text-[var(--ds-heading)]">
                {WEEKDAYS_SAT_FIRST[index]} <span className="tabular-nums">{jd}</span> {JALALI_MONTHS[jm - 1]}
              </h4>
              {items.length === 0 && <p className="text-xs text-[var(--ds-text-muted)]">—</p>}
              <ul className="ds-week-list space-y-1">
                {items.map((item) => (
                  <li key={item.appointment_id} data-testid="week-item">
                    <button
                      type="button"
                      disabled={!onOpen}
                      onClick={() => onOpen?.(item)}
                      title={`${item.patient_first_name} ${item.patient_last_name} — ${item.service_name}`}
                      className="block w-full min-w-0 space-y-1 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-2 py-1.5 text-start text-xs transition-colors hover:border-[var(--ds-primary)] hover:bg-[var(--ds-surface-muted)] disabled:cursor-default"
                    >
                      <span className="flex min-w-0 gap-1.5">
                        <span className="flex-none tabular-nums font-medium">{formatTehranTime(item.scheduled_start_at_utc)}</span>
                        <span className="truncate">
                          {item.patient_first_name} {item.patient_last_name}
                        </span>
                      </span>
                      <span className="block truncate text-[var(--ds-text-muted)]">{item.service_name}</span>
                      <StatusBadge tone={appointmentStatusTone(item.status)}>{appointmentStatusLabel(item.status)}</StatusBadge>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
