"use client";

import Link from "next/link";
import { EmptyState } from "@/components/feedback/EmptyState";
import { Alert } from "@/components/feedback/Alert";
import { BookingChannelIndicator } from "@/components/dashboard/BookingChannelIndicator";
import { FinancialStatusCell } from "@/components/dashboard/FinancialStatusCell";
import { OperationalStatusBadge } from "@/components/dashboard/OperationalStatusBadge";
import { PaginationFooter } from "@/components/dashboard/PaginationFooter";
import { DataTable } from "@/components/tables/DataTable";
import { Skeleton } from "@/components/ui/Skeleton";
import { Icon } from "@/components/ui/Icon";
import { apiJson } from "@/lib/api";
import { formatTehran } from "@/lib/client";
import { formatTehranTime } from "@/lib/format/jalali";
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

type Adv = { gender: string; channel: string };

type Props = {
  today: string;
  query: DayQuery;
  can: (code: string) => boolean;
  filterKey?: string;
  filterLabel: string;
  search: string;
  onSearchChange: (value: string) => void;
  pageSize: (typeof DAY_PAGE_SIZES)[number];
  onPageSizeChange: (value: (typeof DAY_PAGE_SIZES)[number]) => void;
  offset: number;
  onOffsetChange: (value: number) => void;
  total: number;
  onOpenFinance?: (target: FinanceDrawerTarget) => void;
  filtersOpen: boolean;
  onToggleFilters: () => void;
  activeFilterCount: number;
  onClearMetric?: () => void;
  onClearAll: () => void;
  adv: Adv;
  onAdvChange: (next: Adv) => void;
  onlineReview: "all" | "unreviewed" | "reviewed";
  onOnlineReviewChange: (v: "all" | "unreviewed" | "reviewed") => void;
  onMutated?: () => void;
};

function needsStatus(row: CalendarItem, now: number): boolean {
  if (row.status === "CANCELLED" || row.status === "COMPLETED" || row.status === "NO_SHOW") return false;
  if (row.status === "CHECKED_IN") return true;
  return now > 0 && Date.parse(row.scheduled_end_at_utc) <= now && row.status === "CONFIRMED";
}

/** Server-paginated schedule — metric cards drive the server metric filter. */
export function TodaySchedule({
  today,
  query,
  can,
  filterKey = "today",
  filterLabel,
  search,
  onSearchChange,
  pageSize,
  onPageSizeChange,
  offset,
  onOffsetChange,
  total,
  onOpenFinance,
  filtersOpen,
  onToggleFilters,
  activeFilterCount,
  onClearMetric,
  onClearAll,
  adv,
  onAdvChange,
  onlineReview,
  onOnlineReviewChange,
  onMutated,
}: Props) {
  const now = useNow();
  const items = query.data?.items ?? [];
  const isOnline = filterKey === "online";
  const initialLoad = query.loading && !query.data;

  async function markReviewed(appointmentId: string) {
    await apiJson(`/api/v1/dashboard/online-bookings/${appointmentId}/review`, {
      method: "POST",
      body: {},
    });
    onMutated?.();
  }

  return (
    <section className="space-y-3" aria-label="برنامهٔ امروز" data-testid="today-schedule">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="ds-section-title" data-testid="schedule-title">
          {filterLabel}
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          {onClearMetric ? (
            <button type="button" className="ds-chip-filter" data-testid="active-metric-chip" onClick={onClearMetric}>
              {filterLabel}
              <Icon name="close" size="sm" />
              <span className="sr-only">حذف پالایه شاخص</span>
            </button>
          ) : null}
          {activeFilterCount > 0 ? (
            <button type="button" className="ds-btn ds-btn-ghost ds-btn-sm" data-testid="clear-all-filters" onClick={onClearAll}>
              پاک‌سازی همه
            </button>
          ) : null}
          <Link
            href={`/appointments?date=${today}&view=list`}
            className="ds-btn ds-btn-subtle inline-flex items-center gap-1"
            data-testid="goto-appointments-mgmt"
          >
            مدیریت نوبت‌ها
            <Icon name="chevronLeft" size="sm" />
          </Link>
        </div>
      </div>

      <div className="ds-day-toolbar" data-testid="dashboard-day-toolbar">
        <div className="ds-day-toolbar-search">
          <button
            type="button"
            className="ds-btn ds-btn-ghost ds-filter-trigger"
            aria-expanded={filtersOpen}
            aria-label="پالایه پیشرفته"
            data-testid="filter-toggle"
            data-active={activeFilterCount > 0 || undefined}
            onClick={onToggleFilters}
          >
            <Icon name="filter" />
            {activeFilterCount > 0 ? <span className="ds-filter-dot" aria-hidden="true" /> : null}
          </button>
          <input
            className="ds-input ds-day-search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="جستجوی سریع…"
            data-testid="dashboard-day-search"
            aria-label="جستجوی سریع"
          />
        </div>
      </div>

      <div
        className={`ds-adv-filters${filtersOpen ? " is-open" : ""}`}
        data-testid="advanced-filters"
        hidden={!filtersOpen}
      >
        <div className="ds-adv-filters-grid">
          <label className="text-sm">
            کانال رزرو
            <select
              className="ds-input mt-1"
              value={adv.channel}
              onChange={(e) => onAdvChange({ ...adv, channel: e.target.value })}
              data-testid="filter-channel"
            >
              <option value="">همه</option>
              <option value="ONLINE_WEB">سایت</option>
              <option value="ONLINE_BOT">ربات</option>
              <option value="MANUAL_STAFF">دستی</option>
            </select>
          </label>
          <label className="text-sm">
            جنسیت
            <select
              className="ds-input mt-1"
              value={adv.gender}
              onChange={(e) => onAdvChange({ ...adv, gender: e.target.value })}
              data-testid="filter-gender"
            >
              <option value="">همه</option>
              <option value="FEMALE">زن</option>
              <option value="MALE">مرد</option>
            </select>
          </label>
          {isOnline ? (
            <label className="text-sm">
              وضعیت بررسی
              <select
                className="ds-input mt-1"
                value={onlineReview}
                onChange={(e) => onOnlineReviewChange(e.target.value as typeof onlineReview)}
                data-testid="filter-online-review"
              >
                <option value="all">همه رزروهای آنلاین</option>
                <option value="unreviewed">بررسی‌نشده</option>
                <option value="reviewed">بررسی‌شده</option>
              </select>
            </label>
          ) : null}
        </div>
        <button type="button" className="ds-btn ds-btn-ghost ds-btn-sm mt-2" data-testid="adv-clear" onClick={onClearAll}>
          پاک کردن پالایه‌ها
        </button>
      </div>

      {query.error ? <Alert>{query.error.message}</Alert> : null}
      {initialLoad ? <Skeleton className="h-40" /> : null}
      {query.data ? (
        <DataTable
          rows={items}
          rowKey={(row) => row.appointment_id}
          rowTestId="dashboard-row"
          busy={false}
          refreshing={query.refreshing}
          minWidth="56rem"
          className="ds-schedule-table"
          empty={
            <EmptyState
              icon="calendar"
              title={total === 0 && !search ? "نوبتی برای این مجموعه ثبت نشده" : "هیچ نوبتی با این پالایه نیست"}
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
              className: "ds-cell-center",
              width: "16%",
              cell: (row) => (
                <span className="ds-cell-stack">
                  <span className="inline-flex items-center justify-center gap-1.5">
                    <BookingChannelIndicator channel={row.booking_channel} />
                    <Link href={`/patients/${row.patient_profile_id}`} className="hover:underline">
                      {row.patient_first_name} {row.patient_last_name}
                    </Link>
                  </span>
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
              className: "ds-cell-center",
              width: "16%",
              cell: (row) => (
                <span className="ds-cell-stack text-sm">
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
              width: "9%",
              className: "ds-cell-center tabular-nums whitespace-nowrap",
              cell: (row) => (
                <span className="ds-cell-stack" title={formatTehran(row.scheduled_start_at_utc)}>
                  <span>{formatTehranTime(row.scheduled_start_at_utc)}</span>
                  {isOnline && row.created_at_utc ? (
                    <span className="text-xs text-[var(--ds-text-muted)]" title="زمان تأیید رزرو">
                      رزرو: {formatTehranTime(row.created_at_utc)}
                    </span>
                  ) : null}
                </span>
              ),
            },
            {
              key: "service",
              header: "خدمت درمانی",
              className: "ds-cell-center",
              width: "19%",
              cell: (row) => (
                <span className="ds-cell-stack">
                  <span>{row.service_name}</span>
                  <span className="text-xs text-[var(--ds-text-muted)]">
                    {row.practitioner_name || "بدون ارائه‌دهنده تخصیص‌یافته"}
                  </span>
                </span>
              ),
            },
            {
              key: "finance",
              header: "وضعیت مالی",
              className: "ds-cell-center",
              width: "20%",
              cell: (row) => (
                <FinancialStatusCell
                  code={row.financial_status_code}
                  label={row.financial_status_label}
                  outstandingIrr={row.outstanding_irr}
                  paymentMethodLabel={row.payment_method_label}
                  financeReviewRequired={row.finance_review_required}
                  canOpen={Boolean(onOpenFinance && can(P.financeInvoiceView))}
                  onOpen={
                    onOpenFinance
                      ? () =>
                          onOpenFinance({
                            appointmentId: row.appointment_id,
                            patientId: row.patient_profile_id,
                            patientName: `${row.patient_first_name} ${row.patient_last_name}`,
                            serviceName: row.service_name,
                          })
                      : undefined
                  }
                />
              ),
            },
            {
              key: "ops",
              header: "عملیات پذیرش",
              width: "20%",
              className: "ds-cell-center",
              cell: (row) => (
                <span className="ds-cell-stack gap-1">
                  <OperationalStatusBadge
                    status={row.status}
                    needsStatus={needsStatus(row, now)}
                    appointmentId={row.appointment_id}
                  />
                  {isOnline && row.online_reviewed !== true ? (
                    <button
                      type="button"
                      className="ds-btn ds-btn-sm ds-btn-subtle"
                      data-testid="online-mark-reviewed"
                      onClick={() => void markReviewed(row.appointment_id)}
                    >
                      بررسی شد
                    </button>
                  ) : null}
                </span>
              ),
            },
          ]}
        />
      ) : null}

      {query.data ? (
        <PaginationFooter
          total={total}
          pageSize={pageSize}
          offset={offset}
          pageSizes={DAY_PAGE_SIZES}
          onPageSizeChange={(size) => onPageSizeChange(size as (typeof DAY_PAGE_SIZES)[number])}
          onOffsetChange={onOffsetChange}
        />
      ) : null}
    </section>
  );
}
