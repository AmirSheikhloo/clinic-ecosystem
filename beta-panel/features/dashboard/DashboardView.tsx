"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { DataTable } from "@/components/tables/DataTable";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import type { IconName } from "@/components/ui/icon-paths";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { buildQuery } from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatTehran, tehranDayBoundsUtc, tehranTodayYmd } from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";
import { formatJalaliFromTehranYmd, formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
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

  const showCards = {
    appointments: loading || !!data?.appointments,
    patients: loading || data?.patients_active !== null,
    staff: loading || data?.staff_active !== null,
    services: loading || data?.services_active !== null,
    resources: loading || data?.resources_active !== null,
  };
  const quickActions: Array<{ href: string; label: string; hint: string; icon: IconName; allowed: boolean }> = [
    { href: "/desk", label: "نوبت‌دهی جدید", hint: "میز پذیرش", icon: "desk", allowed: can(P.appointmentsSchedule) },
    { href: "/patients", label: "ثبت و جستجوی بیمار", hint: "فهرست بیماران", icon: "patients", allowed: can(P.patientsSearch) || can(P.patientsRegister) },
    { href: "/appointments", label: "تقویم نوبت‌ها", hint: "نمای روز، هفته و ماه", icon: "calendar", allowed: can(P.appointmentsList) },
    { href: "/catalog", label: "خدمات و منابع", hint: "تعرفه و الزامات", icon: "catalog", allowed: can(P.catalogServicesRead) },
  ];
  const actions = quickActions.filter((item) => item.allowed);

  return (
    <main className="space-y-6" data-testid="dashboard-page">
      <PageHeader
        title="داشبورد"
        description={`خلاصهٔ امروز، ${formatJalaliFromTehranYmd(today)} — فقط دادهٔ مجاز برای حساب شما نمایش داده می‌شود.`}
        actions={
          <Button variant="ghost" icon="refresh" loading={summary.loading || upcoming.loading} onClick={() => setRefresh((v) => v + 1)} data-testid="dashboard-refresh">
            به‌روزرسانی
          </Button>
        }
      />

      {summary.error ? <Alert>{summary.error.message}</Alert> : null}

      {actions.length ? (
        <section aria-label="دسترسی سریع" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" data-testid="dashboard-quick-actions">
          {actions.map((item) => (
            <Link key={item.href} href={item.href} className="ds-card flex items-center gap-3 p-3 transition-colors hover:border-[var(--ds-primary)]">
              <span className="ds-avatar !h-10 !w-10 !rounded-[var(--ds-radius-md)]"><Icon name={item.icon} /></span>
              <span className="min-w-0">
                <span className="block font-semibold text-[var(--ds-heading)]">{item.label}</span>
                <span className="block text-xs text-[var(--ds-text-muted)]">{item.hint}</span>
              </span>
            </Link>
          ))}
        </section>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5" aria-label="شاخص‌ها">
        {showCards.appointments ? <StatCard icon="calendar" label="نوبت‌های امروز" value={count(data?.appointments?.total, loading)} testId="dashboard-count" href={can(P.appointmentsList) ? "/appointments" : undefined} /> : null}
        {showCards.patients ? <StatCard icon="patients" label="بیماران فعال" value={count(data?.patients_active, loading)} testId="dashboard-patients" href={can(P.patientsSearch) ? "/patients" : undefined} /> : null}
        {showCards.staff ? <StatCard icon="staff" label="کارکنان فعال" value={count(data?.staff_active, loading)} testId="dashboard-staff" href={can(P.staffView) ? "/staff" : undefined} /> : null}
        {showCards.services ? <StatCard icon="catalog" label="خدمات فعال" value={count(data?.services_active, loading)} testId="dashboard-services" href={can(P.catalogServicesRead) ? "/catalog" : undefined} /> : null}
        {showCards.resources ? <StatCard icon="layers" label="منابع فعال" value={count(data?.resources_active, loading)} testId="dashboard-resources" href={can(P.resourcesRead) ? "/catalog" : undefined} /> : null}
      </section>

      {data?.appointments && Object.keys(byStatus).length > 0 ? (
        <section aria-label="وضعیت نوبت‌های امروز" className="flex flex-wrap items-center gap-2" data-testid="dashboard-by-status">
          <span className="text-sm text-[var(--ds-text-muted)]">به تفکیک وضعیت:</span>
          {Object.entries(byStatus).map(([key, value]) => (
            <StatusBadge key={key} tone={appointmentStatusTone(key)}>{appointmentStatusLabel(key)}: <span className="ms-1 tabular-nums">{formatCount(value)}</span></StatusBadge>
          ))}
        </section>
      ) : null}

      {can(P.appointmentsList) ? (
        <section className="space-y-3" aria-label="برنامهٔ امروز">
          <div className="flex items-center justify-between">
            <h2 className="ds-section-title">برنامهٔ امروز</h2>
            <Link href={`/appointments?date=${today}`} className="ds-btn ds-btn-subtle ds-btn-sm">مشاهدهٔ تقویم</Link>
          </div>
          {upcoming.error ? <Alert>{upcoming.error.message}</Alert> : null}
          {upcoming.loading && !upcoming.data ? <Skeleton className="h-40" /> : null}
          {upcoming.data ? (
            <DataTable
              rows={upcoming.data.items}
              rowKey={(r) => r.appointment_id}
              rowTestId="dashboard-row"
              empty={
                <EmptyState
                  icon="calendar"
                  title="نوبتی برای امروز ثبت نشده است"
                  description="از میز پذیرش می‌توانید نوبت دستی ثبت کنید."
                  action={can(P.appointmentsSchedule) ? <Link href="/desk" className="ds-btn ds-btn-primary">رفتن به میز پذیرش</Link> : undefined}
                />
              }
              columns={[
                { key: "time", header: "زمان", className: "tabular-nums whitespace-nowrap", cell: (r) => <span title={formatTehran(r.scheduled_start_at_utc)}>{formatTehranTime(r.scheduled_start_at_utc)}</span> },
                { key: "patient", header: "بیمار", className: "font-medium", cell: (r) => `${r.patient_first_name} ${r.patient_last_name}` },
                { key: "service", header: "خدمت", cell: (r) => r.service_name },
                { key: "status", header: "وضعیت", cell: (r) => <StatusBadge tone={appointmentStatusTone(r.status)}>{appointmentStatusLabel(r.status)}</StatusBadge> },
              ]}
            />
          ) : null}
          {upcoming.data?.truncated || (upcoming.data && upcoming.data.items.length >= 8) ? (
            <p className="ds-hint">فقط 8 نوبت نخست نمایش داده می‌شود؛ فهرست کامل را در تقویم ببینید.</p>
          ) : null}
        </section>
      ) : null}

      {!loading && data && !data.appointments && data.patients_active === null && data.staff_active === null && data.services_active === null && data.resources_active === null ? (
        <EmptyState icon="info" title="برای حساب شما شاخصی قابل نمایش نیست" description="مجوزهای لازم برای مشاهدهٔ آمار تخصیص داده نشده است." />
      ) : null}
    </main>
  );
}
