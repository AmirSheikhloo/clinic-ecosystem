"use client";

import { SelectField } from "@/components/forms/SelectField";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import {
  JALALI_MONTHS,
  formatRangeTitle,
  fromJalali,
  jalaliParts,
  stepView,
  type CalendarView,
} from "@/lib/calendar/jalali-grid";
import { formatCount } from "@/lib/format/numbers";
import { appointmentStatusLabel } from "@/lib/format/status";
import { tehranTodayYmd } from "@/lib/client";
import { CALENDAR_STATUSES, type SortKey } from "./types";

export type CalendarFilters = { serviceId: string; resourceId: string; status: string };
export type Option = { id: string; label: string };

type Props = {
  view: CalendarView;
  onViewChange: (view: CalendarView) => void;
  anchor: string;
  onAnchorChange: (ymd: string) => void;
  count: number;
  filters: CalendarFilters;
  onFiltersChange: (filters: CalendarFilters) => void;
  services: Option[];
  resources: Option[];
  sortKey: SortKey;
  onSortKeyChange: (key: SortKey) => void;
};

const VIEWS: Array<{ id: CalendarView; label: string }> = [
  { id: "day", label: "روزانه" },
  { id: "week", label: "هفتگی" },
  { id: "month", label: "ماهانه" },
];

export function CalendarToolbar(props: Props) {
  const { view, anchor, onAnchorChange, filters, onFiltersChange } = props;
  const parts = jalaliParts(anchor);
  const stepLabel = view === "day" ? "روز" : view === "week" ? "هفته" : "ماه";

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[var(--ds-primary-strong)]">نوبت‌های روز</h2>
          <p className="text-[var(--ds-text-muted)]">
            <span data-testid="calendar-title">{formatRangeTitle(view, anchor)}</span> · تعداد:{" "}
            <span className="tabular-nums" data-testid="appointments-count">
              {formatCount(props.count)}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div role="group" aria-label="نمای تقویم" className="flex overflow-hidden rounded-[var(--ds-radius-md)] border border-[var(--ds-border-strong)]">
            {VIEWS.map((v) => (
              <button
                key={v.id}
                type="button"
                aria-pressed={view === v.id}
                data-testid={`view-${v.id}`}
                className={`px-3 py-2 text-sm ${view === v.id ? "bg-[var(--ds-primary)] text-white" : "bg-[var(--ds-surface)]"}`}
                onClick={() => props.onViewChange(v.id)}
              >
                {v.label}
              </button>
            ))}
          </div>
          <Button variant="ghost" onClick={() => onAnchorChange(tehranTodayYmd())} data-testid="calendar-today">امروز</Button>
          <Button variant="ghost" onClick={() => onAnchorChange(stepView(view, anchor, -1))} data-testid="calendar-prev">{stepLabel} قبل</Button>
          <Button variant="ghost" onClick={() => onAnchorChange(stepView(view, anchor, 1))} data-testid="calendar-next">{stepLabel} بعد</Button>
          <TextField
            type="date"
            data-testid="appointments-date"
            label="تاریخ (مرز تهران)"
            value={anchor}
            onChange={(e) => e.target.value && onAnchorChange(e.target.value)}
          />
        </div>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <SelectField
          label="ماه جلالی"
          value={String(parts.jm)}
          data-testid="jalali-month"
          onChange={(e) => onAnchorChange(fromJalali(parts.jy, Number(e.target.value), parts.jd))}
        >
          {JALALI_MONTHS.map((name, index) => (
            <option key={name} value={index + 1}>{name}</option>
          ))}
        </SelectField>
        <div className="flex items-center gap-1 pb-1 text-sm">
          <Button variant="ghost" aria-label="سال قبل" onClick={() => onAnchorChange(fromJalali(parts.jy - 1, parts.jm, parts.jd))}>‹</Button>
          <span className="min-w-12 text-center tabular-nums" data-testid="jalali-year">{parts.jy}</span>
          <Button variant="ghost" aria-label="سال بعد" onClick={() => onAnchorChange(fromJalali(parts.jy + 1, parts.jm, parts.jd))}>›</Button>
        </div>
        <SelectField label="خدمت" value={filters.serviceId} data-testid="filter-service" onChange={(e) => onFiltersChange({ ...filters, serviceId: e.target.value })}>
          <option value="">همه</option>
          {props.services.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </SelectField>
        <SelectField label="منبع" value={filters.resourceId} data-testid="filter-resource" onChange={(e) => onFiltersChange({ ...filters, resourceId: e.target.value })}>
          <option value="">همه</option>
          {props.resources.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </SelectField>
        <SelectField label="وضعیت" value={filters.status} data-testid="filter-status" onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}>
          <option value="">همه</option>
          {CALENDAR_STATUSES.map((s) => <option key={s} value={s}>{appointmentStatusLabel(s)}</option>)}
        </SelectField>
        {view === "day" && (
          <SelectField label="مرتب‌سازی" value={props.sortKey} onChange={(e) => props.onSortKeyChange(e.target.value as SortKey)}>
            <option value="time">زمان</option>
            <option value="patient">بیمار</option>
            <option value="service">خدمت</option>
          </SelectField>
        )}
      </div>
    </div>
  );
}
