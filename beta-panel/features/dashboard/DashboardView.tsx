"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { buildQuery } from "@/lib/api";
import { tehranDayBoundsUtc, tehranTodayYmd } from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";
import { formatJalaliFromTehranYmd } from "@/lib/format/jalali";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import type { CalendarResponse } from "@/features/appointments/types";
import { DashboardMetrics } from "./DashboardMetrics";
import { QUICK_ACTIONS } from "./quick-actions";
import { TodaySchedule } from "./TodaySchedule";
import { UPCOMING_LIMIT, type Summary } from "./types";

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
    ready && can(P.appointmentsList) ? `/api/v1/appointments/calendar${buildQuery({ ...range, limit: UPCOMING_LIMIT })}` : null,
    "بارگذاری نوبت‌های امروز ناموفق بود",
    refresh,
  );

  const loading = status === "loading" || summary.loading;
  const data = summary.data;
  const byStatus = data?.appointments?.by_status ?? {};
  const actions = QUICK_ACTIONS.filter((item) => item.allowed(can));
  const nothingToShow =
    !loading && data && !data.appointments && data.patients_active === null && data.staff_active === null && data.services_active === null && data.resources_active === null;

  return (
    <main className="space-y-6" data-testid="dashboard-page">
      <PageHeader
        title="داشبورد"
        description={`خلاصهٔ امروز، ${formatJalaliFromTehranYmd(today)} — فقط دادهٔ مجاز برای حساب شما نمایش داده می‌شود.`}
        actions={
          <Button
            variant="ghost"
            icon="refresh"
            loading={summary.refreshing || upcoming.refreshing}
            onClick={() => setRefresh((value) => value + 1)}
            data-testid="dashboard-refresh"
          >
            به‌روزرسانی
          </Button>
        }
      />

      {summary.error ? <Alert>{summary.error.message}</Alert> : null}

      {actions.length ? (
        <section aria-label="دسترسی سریع" className="ds-quick-grid" data-testid="dashboard-quick-actions">
          {actions.map((item) => (
            <Link key={item.href} href={item.href} className="ds-card ds-quick-action">
              <span className="ds-avatar !h-10 !w-10 !rounded-[var(--ds-radius-md)]">
                <Icon name={item.icon} />
              </span>
              <span className="min-w-0">
                <span className="block truncate font-semibold text-[var(--ds-heading)]">{item.label}</span>
                <span className="block truncate text-xs text-[var(--ds-text-muted)]">{item.hint}</span>
              </span>
            </Link>
          ))}
        </section>
      ) : null}

      <DashboardMetrics data={data} loading={loading} can={can} today={today} />

      {data?.appointments && Object.keys(byStatus).length > 0 ? (
        <section aria-label="وضعیت نوبت‌های امروز" className="flex flex-wrap items-center gap-2" data-testid="dashboard-by-status">
          <span className="text-sm text-[var(--ds-text-muted)]">به تفکیک وضعیت:</span>
          {Object.entries(byStatus).map(([key, value]) => (
            <Link key={key} href={`/appointments?date=${today}&view=day&status=${key}`} className="rounded-full" title="نمایش در تقویم">
              <StatusBadge tone={appointmentStatusTone(key)}>
                {appointmentStatusLabel(key)}: <span className="ms-1 tabular-nums">{formatCount(value)}</span>
              </StatusBadge>
            </Link>
          ))}
        </section>
      ) : null}

      {can(P.appointmentsList) ? <TodaySchedule today={today} query={upcoming} can={can} /> : null}

      {nothingToShow ? (
        <EmptyState icon="info" title="برای حساب شما شاخصی قابل نمایش نیست" description="مجوزهای لازم برای مشاهدهٔ آمار تخصیص داده نشده است." />
      ) : null}
    </main>
  );
}
