"use client";

import Link from "next/link";
import { EmptyState } from "@/components/feedback/EmptyState";
import { Alert } from "@/components/feedback/Alert";
import { DataTable } from "@/components/tables/DataTable";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StatusNeedsAttentionBadge } from "@/components/ui/StatusNeedsAttentionBadge";
import { Icon } from "@/components/ui/Icon";
import { formatTehran } from "@/lib/client";
import { formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
import { P } from "@/lib/permissions";
import { useNow } from "@/lib/use-now";
import type { CalendarItem } from "@/features/appointments/types";
import type { FinanceDrawerTarget } from "@/features/finance/AppointmentFinanceDrawer";
import { DAY_PAGE_SIZES } from "./types";

type DayQuery = {
  data: { items: CalendarItem[]; total?: number } | null;
  error: { message: string } | null;
  loading: boolean;
  refreshing: boolean;
};

type Props = {
  today: string;
  query: DayQuery;
  can: (code: string) => boolean;
  filterKey?: string;
  search: string;
  onSearchChange: (value: string) => void;
  pageSize: (typeof DAY_PAGE_SIZES)[number];
  onPageSizeChange: (value: (typeof DAY_PAGE_SIZES)[number]) => void;
  offset: number;
  onOffsetChange: (value: number) => void;
  total: number;
  onOpenFinance?: (target: FinanceDrawerTarget) => void;
};

function needsStatus(row: CalendarItem, now: number): boolean {
  if (row.status === "CANCELLED" || row.status === "COMPLETED" || row.status === "NO_SHOW") return false;
  if (row.status === "CHECKED_IN") return true;
  return now > 0 && Date.parse(row.scheduled_end_at_utc) <= now && row.status === "CONFIRMED";
}

/** Server-paginated today schedule — metric cards drive the server metric filter. */
export function TodaySchedule({
  today,
  query,
  can,
  filterKey = "today",
  search,
  onSearchChange,
  pageSize,
  onPageSizeChange,
  offset,
  onOffsetChange,
  total,
  onOpenFinance,
}: Props) {
  const now = useNow();
  const items = query.data?.items ?? [];
  const page = Math.floor(offset / pageSize) + 1;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <section className="space-y-3" aria-label="برنامهٔ امروز" data-testid="today-schedule">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="ds-section-title">نوبت‌های امروز</h2>
        <Link
          href={`/appointments?date=${today}&view=list`}
          className="ds-btn ds-btn-subtle inline-flex items-center gap-1"
          data-testid="goto-appointments-mgmt"
        >
          مدیریت نوبت‌ها
          <Icon name="chevronLeft" size="sm" />
        </Link>
      </div>

      <div className="flex flex-wrap items-end gap-2" data-testid="dashboard-day-toolbar">
        <label className="min-w-[12rem] flex-1 text-sm">
          جستجو
          <input
            className="ds-input mt-1"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="نام بیمار یا خدمت"
            data-testid="dashboard-day-search"
          />
        </label>
        <label className="text-sm">
          در صفحه
          <select
            className="ds-input mt-1"
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value) as (typeof DAY_PAGE_SIZES)[number])}
            data-testid="dashboard-day-page-size"
          >
            {DAY_PAGE_SIZES.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
        <p className="ds-hint ms-auto" data-testid="dashboard-day-total">
          پالایه: {filterKey} · {total} نوبت
        </p>
      </div>

      {query.error ? <Alert>{query.error.message}</Alert> : null}
      {query.loading ? <Skeleton className="h-40" /> : null}
      {query.data ? (
        <DataTable
          rows={items}
          rowKey={(row) => row.appointment_id}
          rowTestId="dashboard-row"
          busy={query.refreshing}
          minWidth="48rem"
          empty={
            <EmptyState
              icon="calendar"
              title={total === 0 && !search ? "نوبتی برای امروز ثبت نشده" : "هیچ نوبتی با این پالایه نیست"}
              description={
                total === 0 && !search
                  ? "از میز پذیرش می‌توانید نوبت دستی ثبت کنید."
                  : "پالایه یا جستجو را تغییر دهید."
              }
              action={
                can(P.appointmentsSchedule) && total === 0 && !search ? (
                  <Link href="/desk" className="ds-btn ds-btn-primary">
                    نوبت‌دهی جدید
                  </Link>
                ) : undefined
              }
            />
          }
          columns={[
            {
              key: "patient",
              header: "نام بیمار",
              className: "font-medium",
              cell: (row) => (
                <span className="inline-flex flex-col">
                  <Link href={`/patients/${row.patient_profile_id}`} className="hover:underline">
                    {row.patient_first_name} {row.patient_last_name}
                  </Link>
                  {row.patient_phone_masked ? (
                    <span className="ltr-isolate text-xs text-[var(--ds-text-muted)]" dir="ltr">
                      {row.patient_phone_masked}
                    </span>
                  ) : null}
                </span>
              ),
            },
            {
              key: "identity",
              header: "کد ملی و بیمه",
              cell: (row) => (
                <span className="inline-flex flex-col text-sm">
                  <span className="ltr-isolate tabular-nums" dir="ltr">
                    {row.national_id_masked || "—"}
                  </span>
                  <span className="text-xs text-[var(--ds-text-muted)]">{row.insurance_label || "بیمه نامشخص"}</span>
                </span>
              ),
            },
            {
              key: "time",
              header: "ساعت",
              width: "7rem",
              className: "tabular-nums whitespace-nowrap",
              cell: (row) => (
                <span title={formatTehran(row.scheduled_start_at_utc)}>{formatTehranTime(row.scheduled_start_at_utc)}</span>
              ),
            },
            {
              key: "service",
              header: "خدمت درمانی",
              cell: (row) => (
                <span className="inline-flex flex-col">
                  <span>{row.service_name}</span>
                  {row.practitioner_name || row.resource_names?.[0] ? (
                    <span className="text-xs text-[var(--ds-text-muted)]">
                      {row.practitioner_name || row.resource_names[0]}
                    </span>
                  ) : null}
                </span>
              ),
            },
            {
              key: "finance",
              header: "وضعیت مالی",
              cell: (row) =>
                onOpenFinance && can(P.financeInvoiceView) ? (
                  <button
                    type="button"
                    className="text-sm text-[var(--ds-primary)] underline-offset-2 hover:underline"
                    data-testid="dashboard-open-finance"
                    onClick={() =>
                      onOpenFinance({
                        appointmentId: row.appointment_id,
                        patientId: row.patient_profile_id,
                        patientName: `${row.patient_first_name} ${row.patient_last_name}`,
                        serviceName: row.service_name,
                      })
                    }
                  >
                    {row.financial_status_label || "مشاهده مالی"}
                  </button>
                ) : (
                  <span className="text-sm text-[var(--ds-text-muted)]">{row.financial_status_label || "—"}</span>
                ),
            },
            {
              key: "ops",
              header: "عملیات پذیرش",
              width: "12rem",
              cell: (row) => (
                <span className="inline-flex flex-col items-start gap-1">
                  <StatusBadge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</StatusBadge>
                  {needsStatus(row, now) ? <StatusNeedsAttentionBadge appointmentId={row.appointment_id} /> : null}
                </span>
              ),
            },
          ]}
        />
      ) : null}

      {total > pageSize ? (
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            className="ds-btn ds-btn-ghost ds-btn-sm"
            disabled={offset <= 0}
            onClick={() => onOffsetChange(Math.max(0, offset - pageSize))}
          >
            قبلی
          </button>
          <span className="ds-hint tabular-nums">
            صفحه {page} از {pages}
          </span>
          <button
            type="button"
            className="ds-btn ds-btn-ghost ds-btn-sm"
            disabled={offset + pageSize >= total}
            onClick={() => onOffsetChange(offset + pageSize)}
          >
            بعدی
          </button>
        </div>
      ) : null}
    </section>
  );
}
