"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { buildQuery } from "@/lib/api";
import { shiftTehranYmd, tehranDayBoundsUtc, tehranTodayYmd } from "@/lib/client";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import type { UpcomingResponse } from "@/features/appointments/types";
import { DashboardMetrics } from "./DashboardMetrics";
import { resolveDashboardAudience } from "./dashboard-role";
import { buildMetricCards } from "./metric-cards";
import { quickActionsFor } from "./quick-actions";
import { TodaySchedule } from "./TodaySchedule";
import { UPCOMING_LIMIT, type Summary } from "./types";

const POLL_MS = 20_000;

export function DashboardView() {
  const { can, status, me } = useSession();
  const [refresh, setRefresh] = useState(0);
  const [activeFilter, setActiveFilter] = useState<string>("today");
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

  const bump = useCallback(() => setRefresh((value) => value + 1), []);

  // Automatic refresh: interval when visible, immediate on focus (§7).
  useEffect(() => {
    if (!ready) return;
    let timer: number | undefined;
    const schedule = () => {
      if (document.visibilityState === "hidden") return;
      timer = window.setInterval(bump, POLL_MS);
    };
    const onVis = () => {
      if (timer) window.clearInterval(timer);
      if (document.visibilityState === "visible") {
        bump();
        schedule();
      }
    };
    const onFocus = () => bump();
    schedule();
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("focus", onFocus);
    return () => {
      if (timer) window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVis);
      window.removeEventListener("focus", onFocus);
    };
  }, [ready, bump]);

  if (status === "loading") return <PageSkeleton />;
  const loading = summary.loading;
  const data = summary.data;
  const cards = buildMetricCards(audience, can, today, tomorrow, data).map((card) => ({
    ...card,
    // Operational cards filter the local schedule instead of navigating away.
    onActivate:
      audience.composition === "operational" && card.href.startsWith("#dash-")
        ? () => setActiveFilter(card.href.replace("#dash-", ""))
        : undefined,
  }));
  const actions = quickActionsFor(audience).filter((item) => item.allowed(can));
  const nothingToShow = !loading && cards.length === 0 && actions.length === 0 && !can(P.appointmentsList);

  return (
    <main className="space-y-5" data-testid="dashboard-page" data-dashboard={audience.composition}>
      <PageHeader
        title={audience.composition === "management" ? "داشبورد مدیریت" : "میز کار پذیرش"}
        description={audience.label}
      />

      {summary.error ? <Alert testId="dashboard-error">{summary.error.message}</Alert> : null}

      {actions.length ? (
        <section aria-label="دسترسی سریع" className="ds-quick-grid ds-quick-grid-3" data-testid="dashboard-quick-actions">
          {actions.map((item) => (
            <Link key={`${item.href}-${item.label}`} href={item.href} className="ds-card ds-quick-action ds-quick-action-row">
              <span className="ds-avatar !h-10 !w-10 !rounded-[var(--ds-radius-md)]" data-accent="action">
                <Icon name={item.icon} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold text-[var(--ds-heading)]">{item.label}</span>
                <span className="block truncate text-xs text-[var(--ds-text-muted)]">{item.hint}</span>
              </span>
              <Icon name="chevronLeft" className="text-[var(--ds-text-muted)]" aria-hidden="true" />
            </Link>
          ))}
        </section>
      ) : null}

      <DashboardMetrics
        cards={cards}
        loading={loading}
        activeKey={activeFilter}
        onSelect={(key) => setActiveFilter(key === activeFilter ? "today" : key)}
      />

      {can(P.appointmentsList) ? (
        <TodaySchedule today={today} query={upcoming} can={can} filterKey={activeFilter} />
      ) : null}

      {nothingToShow ? (
        <EmptyState icon="info" title="برای حساب شما شاخصی قابل نمایش نیست" description="مجوزهای لازم برای مشاهدهٔ آمار تخصیص داده نشده است." />
      ) : null}
    </main>
  );
}
