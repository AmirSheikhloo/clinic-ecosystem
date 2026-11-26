"use client";

import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { SegmentedControl } from "@/components/forms/SegmentedControl";
import { SelectField } from "@/components/forms/SelectField";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { formatRangeTitle, stepView, type CalendarView } from "@/lib/calendar/jalali-grid";
import { formatCount } from "@/lib/format/numbers";
import { appointmentStatusLabel } from "@/lib/format/status";
import { tehranTodayYmd } from "@/lib/client";
import { CALENDAR_STATUSES, type SortKey, type WorkspaceMode } from "./types";

export type CalendarFilters = { serviceId: string; resourceId: string; status: string };
export type Option = { id: string; label: string };

type Props = {
  mode: WorkspaceMode;
  onModeChange: (mode: WorkspaceMode) => void;
  anchor: string;
  onAnchorChange: (ymd: string) => void;
  count: number | null;
  loading: boolean;
  onRefresh: () => void;
  filters: CalendarFilters;
  onFiltersChange: (filters: CalendarFilters) => void;
  services: Option[];
  resources: Option[];
  sortKey: SortKey;
  onSortKeyChange: (key: SortKey) => void;
};

const MODES = [
  { value: "list", label: "فهرست", testId: "view-list" },
  { value: "day", label: "روزانه", testId: "view-day" },
  { value: "week", label: "هفتگی", testId: "view-week" },
  { value: "month", label: "ماهانه", testId: "view-month" },
] as const;

const STEP_NOUN: Record<CalendarView, string> = { day: "روز", week: "هفته", month: "ماه" };

export const EMPTY_FILTERS: CalendarFilters = { serviceId: "", resourceId: "", status: "" };

export function CalendarToolbar(props: Props) {
  const { mode, anchor, onAnchorChange, filters, onFiltersChange } = props;
  const calendarMode = mode !== "list";
  const stepMode: CalendarView = mode === "list" ? "day" : mode;
  const noun = STEP_NOUN[stepMode];
  const filtered = !!(filters.serviceId || filters.resourceId || filters.status);
  const title =
    mode === "list"
      ? formatRangeTitle("day", anchor)
      : formatRangeTitle(mode, anchor);

  return (
    <div className="space-y-4">
      <PageHeader
        title="مدیریت نوبت‌ها"
        description={
          <>
            <span data-testid="calendar-title" className="font-medium text-[var(--ds-text)]">
              {title}
            </span>
            {" · "}تعداد نوبت:{" "}
            <span className="inline-block min-w-[1.5ch] tabular-nums" data-testid="appointments-count">
              {props.count === null ? "—" : formatCount(props.count)}
            </span>
          </>
        }
        actions={
          <Button variant="ghost" icon="refresh" loading={props.loading} onClick={props.onRefresh} data-testid="calendar-refresh">
            به‌روزرسانی
          </Button>
        }
      />

      <div className="ds-card ds-calendar-bar p-3">
        <SegmentedControl label="نمای نوبت‌ها" value={mode} options={MODES} onChange={props.onModeChange} testId="calendar-view" />
        <div className="flex items-center gap-1" role="group" aria-label="پیمایش تاریخ">
          <Button
            variant="ghost"
            icon="chevronRight"
            aria-label={`${noun} قبل`}
            title={`${noun} قبل`}
            onClick={() => onAnchorChange(stepView(stepMode, anchor, -1))}
            data-testid="calendar-prev"
          />
          <Button variant="ghost" onClick={() => onAnchorChange(tehranTodayYmd())} data-testid="calendar-today">
            امروز
          </Button>
          <Button
            variant="ghost"
            icon="chevronLeft"
            aria-label={`${noun} بعد`}
            title={`${noun} بعد`}
            onClick={() => onAnchorChange(stepView(stepMode, anchor, 1))}
            data-testid="calendar-next"
          />
        </div>
        <div className="w-44">
          <JalaliDateField label="رفتن به تاریخ" value={anchor} onChange={(ymd) => ymd && onAnchorChange(ymd)} testId="appointments-date" />
        </div>
      </div>

      {calendarMode ? (
        <div className="ds-filter-grid">
          <SelectField label="خدمت" value={filters.serviceId} data-testid="filter-service" onChange={(e) => onFiltersChange({ ...filters, serviceId: e.target.value })}>
            <option value="">همه خدمت‌ها</option>
            {props.services.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </SelectField>
          <SelectField label="منبع" value={filters.resourceId} data-testid="filter-resource" onChange={(e) => onFiltersChange({ ...filters, resourceId: e.target.value })}>
            <option value="">همه منابع</option>
            {props.resources.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </SelectField>
          <SelectField label="وضعیت" value={filters.status} data-testid="filter-status" onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}>
            <option value="">همه وضعیت‌ها</option>
            {CALENDAR_STATUSES.map((s) => (
              <option key={s} value={s}>
                {appointmentStatusLabel(s)}
              </option>
            ))}
          </SelectField>
          <SelectField
            label="مرتب‌سازی فهرست روز"
            value={props.sortKey}
            disabled={mode !== "day"}
            data-testid="sort-select"
            onChange={(e) => props.onSortKeyChange(e.target.value as SortKey)}
          >
            <option value="time">زمان</option>
            <option value="patient">بیمار</option>
            <option value="service">خدمت</option>
          </SelectField>
          <Button variant="subtle" icon="close" disabled={!filtered} onClick={() => onFiltersChange(EMPTY_FILTERS)} data-testid="filters-clear">
            پاک‌کردن فیلترها
          </Button>
        </div>
      ) : null}
    </div>
  );
}
