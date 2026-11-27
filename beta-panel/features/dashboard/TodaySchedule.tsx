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
import type { UpcomingResponse } from "@/features/appointments/types";
import { UPCOMING_LIMIT } from "./types";

type Props = {
  today: string;
  query: { data: UpcomingResponse | null; error: { message: string } | null; loading: boolean; refreshing: boolean };
  can: (code: string) => boolean;
  filterKey?: string;
};

function needsStatus(row: UpcomingResponse["items"][number], now: number): boolean {
  if (row.status === "CANCELLED" || row.status === "COMPLETED" || row.status === "NO_SHOW") return false;
  if (row.status === "CHECKED_IN") return true;
  return now > 0 && Date.parse(row.scheduled_end_at_utc) <= now && row.status === "CONFIRMED";
}

/** Today's schedule — six RTL columns; metric cards filter this table in place. */
export function TodaySchedule({ today, query, can, filterKey = "today" }: Props) {
  const now = useNow();
  const all = query.data?.items ?? [];
  const items = all.filter((row) => {
    if (filterKey === "cancelled") return row.status === "CANCELLED";
    if (filterKey === "upcoming") return row.status === "CONFIRMED" && Date.parse(row.scheduled_start_at_utc) > now;
    if (filterKey === "needs_status") return needsStatus(row, now);
    return true; // today / all
  });

  return (
    <section className="space-y-3" aria-label="برنامهٔ امروز" data-testid="today-schedule">
      <div className="flex items-center justify-between gap-2">
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
              title={all.length === 0 ? "نوبتی برای امروز ثبت نشده" : "هیچ نوبتی با این پالایه نیست"}
              description={all.length === 0 ? "از میز پذیرش می‌توانید نوبت دستی ثبت کنید." : "پالایهٔ کارت شاخص را پاک کنید یا تغییر دهید."}
              action={
                can(P.appointmentsSchedule) && all.length === 0 ? (
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
              cell: (row) => (
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
                  {needsStatus(row, now) ? (
                    <StatusNeedsAttentionBadge appointmentId={row.appointment_id} />
                  ) : null}
                </span>
              ),
            },
          ]}
        />
      ) : null}
      {query.data && all.length >= UPCOMING_LIMIT ? (
        <p className="ds-hint">فقط {UPCOMING_LIMIT} نوبت پیش‌رو نمایش داده می‌شود؛ فهرست کامل را در مدیریت نوبت‌ها ببینید.</p>
      ) : null}
    </section>
  );
}
