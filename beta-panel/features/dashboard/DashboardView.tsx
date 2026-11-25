"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { buildQuery } from "@/lib/api";
import { formatTehran, tehranDayBoundsUtc, tehranTodayYmd } from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";
import { formatJalaliFromTehranYmd, formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel } from "@/lib/format/status";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import type { CalendarResponse } from "@/features/appointments/types";

type Summary = {
  appointments: { total: number; by_status: Record<string, number> } | null;
  patients_active: number | null;
  staff_active: number | null;
  services_active: number | null;
  resources_active: number | null;
};

const count = (value: number | null | undefined, loading: boolean) =>
  loading ? "…" : value === null || value === undefined ? "—" : formatCount(value);

export function DashboardView() {
  const { can, status } = useSession();
  const [refresh, setRefresh] = useState(0);
  const today = tehranTodayYmd();
  const { start, end } = useMemo(() => tehranDayBoundsUtc(today), [today]);
  const range = { start_at_utc: start, end_at_utc: end };
  const ready = status === "ready";

  const summary = useApiQuery<Summary>(
    ready ? `/api/v1/dashboard/summary${buildQuery(range)}` : null,
    "بارگذاری آمار داشبورد ناموفق بود",
    refresh,
  );
  const upcoming = useApiQuery<CalendarResponse>(
    ready && can(P.appointmentsList) ? `/api/v1/appointments/calendar${buildQuery({ ...range, limit: 8 })}` : null,
    "بارگذاری نوبت‌های امروز ناموفق بود",
    refresh,
  );

  const loading = status === "loading" || (summary.loading && !summary.data);
  const data = summary.data;
  const byStatus = data?.appointments?.by_status ?? {};

  return (
    <main className="space-y-6 animate-rise" data-testid="dashboard-page">
      <PageHeader
        title="داشبورد پذیرش"
        description={`آمار واقعی روز جاری از دادهٔ مجاز شما — ${formatJalaliFromTehranYmd(today)}`}
        actions={
          <>
            <Button variant="ghost" onClick={() => setRefresh((v) => v + 1)}>تازه‌سازی</Button>
            {can(P.appointmentsSchedule) && <Link href="/desk" className="ds-btn ds-btn-primary">میز پذیرش</Link>}
            {can(P.patientsRegister) && <Link href="/patients" className="ds-btn ds-btn-ghost">ثبت بیمار</Link>}
          </>
        }
      />

      {summary.error && <Alert>{summary.error.message}</Alert>}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="شاخص‌ها">
        {(loading || data?.appointments) && (
          <StatCard label="نوبت‌های امروز" value={count(data?.appointments?.total, loading)} testId="dashboard-count" />
        )}
        {(loading || data?.patients_active !== null) && <StatCard label="بیماران فعال" value={count(data?.patients_active, loading)} testId="dashboard-patients" />}
        {(loading || data?.staff_active !== null) && <StatCard label="کارکنان فعال" value={count(data?.staff_active, loading)} testId="dashboard-staff" />}
        {(loading || data?.services_active !== null) && <StatCard label="خدمات فعال" value={count(data?.services_active, loading)} testId="dashboard-services" />}
        {(loading || data?.resources_active !== null) && <StatCard label="منابع فعال" value={count(data?.resources_active, loading)} testId="dashboard-resources" />}
      </section>

      {data?.appointments && Object.keys(byStatus).length > 0 && (
        <section aria-label="وضعیت نوبت‌های امروز" className="flex flex-wrap gap-2" data-testid="dashboard-by-status">
          {Object.entries(byStatus).map(([key, value]) => (
            <StatusBadge key={key}>{appointmentStatusLabel(key)}: <span className="ms-1 tabular-nums">{formatCount(value)}</span></StatusBadge>
          ))}
        </section>
      )}

      {can(P.appointmentsList) && (
        <section className="space-y-3" aria-label="نوبت‌های پیش‌رو">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">نوبت‌های امروز</h3>
            <Link href="/appointments" className="text-sm text-[var(--ds-primary)] hover:underline">مشاهدهٔ تقویم</Link>
          </div>
          {upcoming.error && <Alert>{upcoming.error.message}</Alert>}
          {upcoming.loading && !upcoming.data && <p className="text-[var(--ds-text-muted)]">در حال بارگذاری…</p>}
          {upcoming.data && (
            <DataTable
              rows={upcoming.data.items}
              rowKey={(r) => r.appointment_id}
              rowTestId="dashboard-row"
              empty={<EmptyState title="نوبتی برای امروز ثبت نشده است" description="از میز پذیرش می‌توانید نوبت دستی ثبت کنید." />}
              columns={[
                { key: "time", header: "زمان", className: "tabular-nums", cell: (r) => <span title={formatTehran(r.scheduled_start_at_utc)}>{formatTehranTime(r.scheduled_start_at_utc)}</span> },
                { key: "patient", header: "بیمار", cell: (r) => `${r.patient_first_name} ${r.patient_last_name}` },
                { key: "service", header: "خدمت", cell: (r) => r.service_name },
                { key: "status", header: "وضعیت", cell: (r) => appointmentStatusLabel(r.status) },
              ]}
            />
          )}
        </section>
      )}

      {!loading && data && !data.appointments && data.patients_active === null && data.staff_active === null && data.services_active === null && data.resources_active === null && (
        <EmptyState title="برای حساب شما شاخصی قابل نمایش نیست" description="مجوزهای لازم برای مشاهدهٔ آمار تخصیص داده نشده است." />
      )}
    </main>
  );
}
