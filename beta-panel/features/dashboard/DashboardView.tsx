"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { buildQuery } from "@/lib/api";
import { shiftTehranYmd, tehranDayBoundsUtc, tehranTodayYmd } from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";
import { appointmentStatusLabel, appointmentStatusTone } from "@/lib/format/status";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import type { UpcomingResponse } from "@/features/appointments/types";
import { DashboardAlerts } from "./DashboardAlerts";
import { DashboardGreeting } from "./DashboardGreeting";
import { DashboardMetrics } from "./DashboardMetrics";
import { resolveDashboardAudience } from "./dashboard-role";
import { buildMetricCards } from "./metric-cards";
import { quickActionsFor } from "./quick-actions";
import { TodaySchedule } from "./TodaySchedule";
import { UPCOMING_LIMIT, type Summary } from "./types";

export function DashboardView() {
  const { can, status, me } = useSession();
  const [refresh, setRefresh] = useState(0);
  const today = tehranTodayYmd();
  const tomorrow = shiftTehranYmd(today, 1);
  const bounds = tehranDayBoundsUtc(today);
  const range = { start_at_utc: bounds.start, end_at_utc: bounds.end };
  const ready = status === "ready";
  const audience = resolveDashboardAudience(me?.governance_roles ?? [], can);

  const summary = useApiQuery<Summary>(
    ready ? `/api/v1/dashboard/summary${buildQuery(range)}` : null,
    "بارگذاری آمار داشبورد ناموفق بود",
    refresh,
  );
  const upcoming = useApiQuery<UpcomingResponse>(
    ready && can(P.appointmentsList)
      ? `/api/v1/appointments/upcoming${buildQuery({ ...range, limit: UPCOMING_LIMIT })}`
      : null,
    "بارگذاری نوبت‌های امروز ناموفق بود",
    refresh,
  );

  if (status === "loading") return <PageSkeleton />;
  const loading = summary.loading;
  const data = summary.data;
  const byStatus = data?.appointments?.by_status ?? {};
  const cards = buildMetricCards(audience, can, today, tomorrow, data);
  const actions = quickActionsFor(audience).filter((item) => item.allowed(can));
  const nothingToShow = !loading && cards.length === 0 && actions.length === 0 && !can(P.appointmentsList);

  return (
    <main className="space-y-6" data-testid="dashboard-page" data-dashboard={audience.composition}>
      <PageHeader
        title={audience.composition === "management" ? "داشبورد مدیریت" : "داشبورد عملیات"}
        description={
          <DashboardGreeting
            todayYmd={today}
            firstName={me?.first_name ?? ""}
            roleLabel={audience.label}
            composition={audience.composition}
          />
        }
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

      {summary.error ? <Alert testId="dashboard-error">{summary.error.message}</Alert> : null}

      {actions.length ? (
        <section aria-label="دسترسی سریع" className="ds-quick-grid" data-testid="dashboard-quick-actions">
          {actions.map((item) => (
            <Link key={`${item.href}-${item.label}`} href={item.href} className="ds-card ds-quick-action">
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

      <DashboardMetrics cards={cards} loading={loading} />

      <DashboardAlerts today={today} summary={data} canList={can(P.appointmentsList)} />

      {can(P.appointmentsList) ? (
        <section aria-label="وضعیت نوبت‌های امروز" className="ds-status-row" data-testid="dashboard-by-status">
          {loading ? <Skeleton className="h-6 w-56" /> : null}
          {!loading && Object.keys(byStatus).length > 0 ? (
            <>
              <span className="text-sm text-[var(--ds-text-muted)]">به تفکیک وضعیت:</span>
              {Object.entries(byStatus).map(([key, value]) => (
                <Link key={key} href={`/appointments?view=list&date=${today}&status=${key}`} className="rounded-full" title="نمایش در فهرست">
                  <StatusBadge tone={appointmentStatusTone(key)}>
                    {appointmentStatusLabel(key)}: <span className="ms-1 tabular-nums">{formatCount(value)}</span>
                  </StatusBadge>
                </Link>
              ))}
            </>
          ) : null}
        </section>
      ) : null}

      {can(P.appointmentsList) ? <TodaySchedule today={today} query={upcoming} can={can} /> : null}

      {nothingToShow ? (
        <EmptyState icon="info" title="برای حساب شما شاخصی قابل نمایش نیست" description="مجوزهای لازم برای مشاهدهٔ آمار تخصیص داده نشده است." />
      ) : null}
    </main>
  );
}
