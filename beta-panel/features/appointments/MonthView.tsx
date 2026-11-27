import { WEEKDAYS_SAT_FIRST, jalaliParts, type VisibleRange } from "@/lib/calendar/jalali-grid";
import { formatCount } from "@/lib/format/numbers";
import { formatTehranTime } from "@/lib/format/jalali";
import { rangeDays } from "./calendar-model";
import type { CalendarItem } from "./types";

type Props = {
  range: VisibleRange;
  anchor: string;
  groups: Map<string, CalendarItem[]>;
  /** Authoritative server-side per-day totals when available (may exceed loaded preview items). */
  dayCounts?: Record<string, number>;
  todayYmd: string;
  onPickDay: (ymd: string) => void;
};

const PREVIEW = 3;

export function MonthView({ range, anchor, groups, dayCounts, todayYmd, onPickDay }: Props) {
  const currentMonth = jalaliParts(anchor).jm;
  const days = rangeDays(range);
  return (
    <div className="overflow-x-auto" data-testid="month-view">
      <div className="grid min-w-[44rem] grid-cols-7 gap-1" role="grid" aria-label="تقویم ماهانه">
        {WEEKDAYS_SAT_FIRST.map((name) => (
          <div key={name} role="columnheader" className="px-2 py-1 text-center text-xs font-medium text-[var(--ds-text-muted)]">
            {name}
          </div>
        ))}
        {days.map((ymd) => {
          const { jd, jm } = jalaliParts(ymd);
          const items = groups.get(ymd) ?? [];
          const count = dayCounts?.[ymd] ?? items.length;
          const outside = jm !== currentMonth;
          return (
            <button
              key={ymd}
              type="button"
              role="gridcell"
              onClick={() => onPickDay(ymd)}
              data-testid="month-cell"
              data-count={count}
              aria-label={`${jd} — ${formatCount(count)} نوبت`}
              className={`ds-card min-h-24 p-2 text-start align-top hover:bg-[var(--ds-surface-muted)] ${outside ? "opacity-50" : ""} ${ymd === todayYmd ? "ring-2 ring-[var(--ds-primary)]" : ""}`}
            >
              <span className="flex items-center justify-between text-sm">
                <span className="tabular-nums font-semibold">{jd}</span>
                {count > 0 && (
                  <span className="ds-badge ds-badge-ok tabular-nums">{formatCount(count)}</span>
                )}
              </span>
              <ul className="mt-1 space-y-0.5 text-xs">
                {items.slice(0, PREVIEW).map((item) => (
                  <li key={item.appointment_id} className="truncate text-[var(--ds-text-muted)]">
                    <span className="tabular-nums">{formatTehranTime(item.scheduled_start_at_utc)}</span>{" "}
                    {item.patient_last_name}
                  </li>
                ))}
                {items.length > PREVIEW && (
                  <li className="text-[var(--ds-primary)]">+{formatCount(items.length - PREVIEW)} دیگر</li>
                )}
              </ul>
            </button>
          );
        })}
      </div>
    </div>
  );
}
