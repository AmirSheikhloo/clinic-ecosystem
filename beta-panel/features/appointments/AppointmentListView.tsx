"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { SearchField } from "@/components/forms/SearchField";
import { SegmentedControl } from "@/components/forms/SegmentedControl";
import { SelectField } from "@/components/forms/SelectField";
import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { buildQuery } from "@/lib/api";
import { formatTehran, shiftTehranYmd, tehranDayBoundsUtc, tehranTodayYmd } from "@/lib/client";
import { formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone, bookingChannelLabel } from "@/lib/format/status";
import { clampOffset } from "@/lib/pagination";
import { useApiQuery } from "@/lib/use-api-query";
import { useDebouncedValue } from "@/lib/use-debounced";
import type { Option } from "./CalendarToolbar";
import {
  CALENDAR_STATUSES,
  LIST_PAGE_SIZES,
  type CalendarItem,
  type ManagementResponse,
  type SortKey,
} from "./types";

type DatePreset = "today" | "tomorrow" | "custom";

type Props = {
  dateYmd: string;
  onDateChange: (ymd: string) => void;
  initialStatus: string;
  services: Option[];
  resources: Option[];
  canOpen: boolean;
  onOpen: (item: CalendarItem) => void;
  refreshKey: number;
  onTotalChange: (total: number | null) => void;
  onLoadingChange: (loading: boolean) => void;
};

const DATE_PRESETS = [
  { value: "today", label: "امروز" },
  { value: "tomorrow", label: "فردا" },
  { value: "custom", label: "سفارشی" },
] as const;

function resolvePreset(ymd: string, today: string): DatePreset {
  if (ymd === today) return "today";
  if (ymd === shiftTehranYmd(today, 1)) return "tomorrow";
  return "custom";
}

export function AppointmentListView({
  dateYmd,
  onDateChange,
  initialStatus,
  services,
  resources,
  canOpen,
  onOpen,
  refreshKey,
  onTotalChange,
  onLoadingChange,
}: Props) {
  const today = tehranTodayYmd();
  const [forceCustom, setForceCustom] = useState(false);
  const preset: DatePreset = forceCustom ? "custom" : resolvePreset(dateYmd, today);
  const [status, setStatus] = useState(initialStatus);
  const [serviceId, setServiceId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [sort, setSort] = useState<SortKey>("time");
  const [limit, setLimit] = useState<(typeof LIST_PAGE_SIZES)[number]>(50);
  const [offset, setOffset] = useState(0);
  const [qDraft, setQDraft] = useState("");
  const q = useDebouncedValue(qDraft.trim(), 350);

  const bounds = tehranDayBoundsUtc(dateYmd);
  const path = useMemo(
    () =>
      `/api/v1/appointments/management${buildQuery({
        start_at_utc: bounds.start,
        end_at_utc: bounds.end,
        service_id: serviceId,
        resource_id: resourceId,
        status,
        q,
        sort,
        limit,
        offset,
      })}`,
    [bounds.start, bounds.end, serviceId, resourceId, status, q, sort, limit, offset],
  );

  const query = useApiQuery<ManagementResponse>(path, "بارگذاری فهرست نوبت‌ها ناموفق بود", refreshKey, {
    keepPrevious: true,
  });

  useEffect(() => {
    onTotalChange(query.data?.total ?? null);
  }, [query.data?.total, onTotalChange]);

  useEffect(() => {
    onLoadingChange(query.loading || query.refreshing);
  }, [query.loading, query.refreshing, onLoadingChange]);

  useEffect(() => {
    setOffset(0);
    if (resolvePreset(dateYmd, today) !== "custom") setForceCustom(false);
  }, [dateYmd, today]);

  function onPresetChange(next: DatePreset) {
    if (next === "today") {
      setForceCustom(false);
      onDateChange(today);
    } else if (next === "tomorrow") {
      setForceCustom(false);
      onDateChange(shiftTehranYmd(today, 1));
    } else {
      setForceCustom(true);
    }
  }

  const data = query.data;
  const safeOffset = data ? clampOffset(data.total, limit, offset) : offset;
  const items = data?.items ?? [];
  const filtered = !!(serviceId || resourceId || status || qDraft.trim() || preset !== "today");

  return (
    <section className="space-y-4" aria-label="فهرست نوبت‌ها" data-testid="appointments-list">
      <div className="ds-card ds-filter-grid p-3">
        <SegmentedControl label="بازه تاریخ" value={preset} options={DATE_PRESETS} onChange={onPresetChange} testId="list-date-preset" />
        {preset === "custom" ? (
          <div className="w-44">
            <JalaliDateField
              label="تاریخ"
              value={dateYmd}
              onChange={(ymd) => {
                if (!ymd) return;
                setForceCustom(true);
                onDateChange(ymd);
              }}
              testId="list-date"
            />
          </div>
        ) : null}
        <div className="ds-filter-wide">
          <SearchField
            label="جستجو"
            value={qDraft}
            onValueChange={(value) => {
              setQDraft(value);
              setOffset(0);
            }}
            busy={query.refreshing}
            placeholder="نام بیمار…"
            data-testid="list-search"
          />
        </div>
        <SelectField label="خدمت" value={serviceId} data-testid="filter-service" onChange={(e) => { setServiceId(e.target.value); setOffset(0); }}>
          <option value="">همه خدمت‌ها</option>
          {services.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </SelectField>
        <SelectField label="منبع" value={resourceId} data-testid="filter-resource" onChange={(e) => { setResourceId(e.target.value); setOffset(0); }}>
          <option value="">همه منابع</option>
          {resources.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </SelectField>
        <SelectField label="وضعیت" value={status} data-testid="filter-status" onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
          <option value="">همه وضعیت‌ها</option>
          {CALENDAR_STATUSES.map((s) => <option key={s} value={s}>{appointmentStatusLabel(s)}</option>)}
        </SelectField>
        <SelectField label="مرتب‌سازی" value={sort} data-testid="list-sort" onChange={(e) => { setSort(e.target.value as SortKey); setOffset(0); }}>
          <option value="time">زمان</option><option value="patient">بیمار</option><option value="service">خدمت</option>
        </SelectField>
        <SelectField label="در صفحه" value={String(limit)} data-testid="list-limit" onChange={(e) => { setLimit(Number(e.target.value) as (typeof LIST_PAGE_SIZES)[number]); setOffset(0); }}>
          {LIST_PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}
        </SelectField>
        <Button
          variant="subtle"
          icon="close"
          disabled={!filtered}
          onClick={() => {
            setServiceId("");
            setResourceId("");
            setStatus("");
            setQDraft("");
            setSort("time");
            setOffset(0);
            setForceCustom(false);
            onDateChange(today);
          }}
          data-testid="filters-clear"
        >
          پاک‌کردن فیلترها
        </Button>
      </div>

      <QueryBoundary loading={query.loading && !query.data} error={query.error} deniedWhat="مشاهدهٔ نوبت‌ها" onRetry={query.reload}>
        {data ? (
          <>
            <DataTable
              rows={items}
              rowKey={(row) => row.appointment_id}
              rowTestId="appointment-row"
              busy={query.refreshing || query.stale}
              minWidth="42rem"
              empty={
                <EmptyState
                  icon="calendar"
                  title="نوبتی با این فیلترها یافت نشد"
                  description="تاریخ یا فیلترها را تغییر دهید، یا از میز پذیرش نوبت ثبت کنید."
                  action={<Link href="/desk" className="ds-btn ds-btn-primary">رفتن به میز پذیرش</Link>}
                />
              }
              columns={[
                {
                  key: "time", header: "زمان", width: "9.5rem", className: "tabular-nums whitespace-nowrap",
                  cell: (row) => (
                    <span title={formatTehran(row.scheduled_start_at_utc)}>
                      {formatTehranTime(row.scheduled_start_at_utc)} – {formatTehranTime(row.scheduled_end_at_utc)}
                    </span>
                  ),
                },
                { key: "patient", header: "بیمار", className: "font-medium", cell: (row) => `${row.patient_first_name} ${row.patient_last_name}` },
                { key: "service", header: "خدمت", cell: (row) => row.service_name },
                { key: "status", header: "وضعیت", width: "8rem", cell: (row) => <StatusBadge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</StatusBadge> },
                { key: "channel", header: "کانال", width: "7rem", cell: (row) => bookingChannelLabel(row.booking_channel) },
                {
                  key: "open", header: "", width: "6.5rem", className: "text-end",
                  cell: (row) => canOpen ? <Button variant="subtle" size="sm" onClick={() => onOpen(row)} data-testid="appointment-open">جزئیات</Button> : null,
                },
              ]}
            />
            {data.total > 0 ? (
              <Pagination total={data.total} limit={limit} offset={safeOffset} onOffsetChange={setOffset} />
            ) : null}
          </>
        ) : null}
      </QueryBoundary>
    </section>
  );
}
