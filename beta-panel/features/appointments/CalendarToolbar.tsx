"use client";

import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { SelectField } from "@/components/forms/SelectField";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { formatRangeTitle, stepView, type CalendarView } from "@/lib/calendar/jalali-grid";
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
  loading: boolean;
  onRefresh: () => void;
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

const STEP_NOUN: Record<CalendarView, string> = { day: "روز", week: "هفته", month: "ماه" };

export const EMPTY_FILTERS: CalendarFilters = { serviceId: "", resourceId: "", status: "" };

export function CalendarToolbar(props: Props) {
  const { view, anchor, onAnchorChange, filters, onFiltersChange } = props;
  const noun = STEP_NOUN[view];
  const filtered = !!(filters.serviceId || filters.resourceId || filters.status);

  return (
    <div className="space-y-4">
      <PageHeader
        title="تقویم نوبت‌ها"
        description={
          <>
            <span data-testid="calendar-title" className="font-medium text-[var(--ds-text)]">{formatRangeTitle(view, anchor)}</span>
            {" · "}تعداد نوبت:{" "}
            <span className="tabular-nums" data-testid="appointments-count">{formatCount(props.count)}</span>
          </>
        }
        actions={
          <Button variant="ghost" icon="refresh" loading={props.loading} onClick={props.onRefresh} data-testid="calendar-refresh">
            به‌روزرسانی
          </Button>
        }
      />

      <div className="ds-card flex flex-wrap items-end gap-x-4 gap-y-3 p-3">
        <div role="group" aria-label="نمای تقویم" className="ds-segmented">
          {VIEWS.map((v) => (
            <button key={v.id} type="button" aria-pressed={view === v.id} data-testid={`view-${v.id}`} onClick={() => props.onViewChange(v.id)}>
              {v.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1" role="group" aria-label="پیمایش تاریخ">
          <Button variant="ghost" icon="chevronRight" aria-label={`${noun} قبل`} title={`${noun} قبل`} onClick={() => onAnchorChange(stepView(view, anchor, -1))} data-testid="calendar-prev" />
          <Button variant="ghost" onClick={() => onAnchorChange(tehranTodayYmd())} data-testid="calendar-today">امروز</Button>
          <Button variant="ghost" icon="chevronLeft" aria-label={`${noun} بعد`} title={`${noun} بعد`} onClick={() => onAnchorChange(stepView(view, anchor, 1))} data-testid="calendar-next" />
        </div>
        <div className="w-44">
          <JalaliDateField label="رفتن به تاریخ" value={anchor} onChange={(ymd) => ymd && onAnchorChange(ymd)} testId="appointments-date" />
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <SelectField label="خدمت" value={filters.serviceId} data-testid="filter-service" onChange={(e) => onFiltersChange({ ...filters, serviceId: e.target.value })}>
          <option value="">همه خدمت‌ها</option>
          {props.services.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </SelectField>
        <SelectField label="منبع" value={filters.resourceId} data-testid="filter-resource" onChange={(e) => onFiltersChange({ ...filters, resourceId: e.target.value })}>
          <option value="">همه منابع</option>
          {props.resources.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </SelectField>
        <SelectField label="وضعیت" value={filters.status} data-testid="filter-status" onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}>
          <option value="">همه وضعیت‌ها</option>
          {CALENDAR_STATUSES.map((s) => <option key={s} value={s}>{appointmentStatusLabel(s)}</option>)}
        </SelectField>
        {view === "day" ? (
          <SelectField label="مرتب‌سازی" value={props.sortKey} onChange={(e) => props.onSortKeyChange(e.target.value as SortKey)}>
            <option value="time">زمان</option>
            <option value="patient">بیمار</option>
            <option value="service">خدمت</option>
          </SelectField>
        ) : null}
        {filtered ? (
          <Button variant="subtle" icon="close" onClick={() => onFiltersChange(EMPTY_FILTERS)} data-testid="filters-clear">
            پاک‌کردن فیلترها
          </Button>
        ) : null}
      </div>
    </div>
  );
}
