"use client";

import Link from "next/link";
import { EmptyState } from "@/components/feedback/EmptyState";
import { Alert } from "@/components/feedback/Alert";
import { DataTable } from "@/components/tables/DataTable";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
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
};

/** Actionable upcoming appointments for today (server-side upcoming query). */
export function TodaySchedule({ today, query, can }: Props) {
  const now = useNow();
  const items = query.data?.items ?? [];
  const nextId = now
    ? items.find((item) => Date.parse(item.scheduled_end_at_utc) > now && item.status !== "CANCELLED")?.appointment_id
    : undefined;
  const finished = (end: string) => now > 0 && Date.parse(end) <= now;

  return (
    <section className="space-y-3" aria-label="برنامهٔ امروز">
      <div className="flex items-center justify-between gap-2">
        <h2 className="ds-section-title">برنامهٔ امروز</h2>
        <Link href={`/appointments?date=${today}&view=list`} className="ds-btn ds-btn-subtle ds-btn-sm">
          مدیریت نوبت‌ها
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
          minWidth="34rem"
          empty={
            <EmptyState
              icon="calendar"
              title="نوبت پیش‌رویی برای امروز نیست"
              description="از میز پذیرش می‌توانید نوبت دستی ثبت کنید."
              action={can(P.appointmentsSchedule) ? <Link href="/desk" className="ds-btn ds-btn-primary">رفتن به میز پذیرش</Link> : undefined}
            />
          }
          columns={[
            {
              key: "time",
              header: "زمان",
              width: "9.5rem",
              className: "tabular-nums whitespace-nowrap",
              cell: (row) => (
                <span title={formatTehran(row.scheduled_start_at_utc)} className={finished(row.scheduled_end_at_utc) ? "text-[var(--ds-text-muted)]" : ""}>
                  {formatTehranTime(row.scheduled_start_at_utc)} – {formatTehranTime(row.scheduled_end_at_utc)}
                </span>
              ),
            },
            {
              key: "patient",
              header: "بیمار",
              className: "font-medium",
              cell: (row) => (
                <span className="inline-flex flex-wrap items-center gap-2">
                  {row.patient_first_name} {row.patient_last_name}
                  {row.appointment_id === nextId ? <StatusBadge tone="info">بعدی</StatusBadge> : null}
                </span>
              ),
            },
            { key: "service", header: "خدمت", cell: (row) => row.service_name },
            {
              key: "status",
              header: "وضعیت",
              width: "8.5rem",
              cell: (row) => <StatusBadge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</StatusBadge>,
            },
          ]}
        />
      ) : null}
      {query.data && items.length >= UPCOMING_LIMIT ? (
        <p className="ds-hint">فقط {UPCOMING_LIMIT} نوبت پیش‌رو نمایش داده می‌شود؛ فهرست کامل را در مدیریت نوبت‌ها ببینید.</p>
      ) : null}
    </section>
  );
}
