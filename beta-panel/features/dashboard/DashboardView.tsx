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
import { METRIC_FILTER_LABELS } from "@/lib/format/operational-status";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import type { ManagementResponse } from "@/features/appointments/types";
import {
  AppointmentFinanceDrawer,
  type FinanceDrawerTarget,
} from "@/features/finance/AppointmentFinanceDrawer";
import { DashboardMetrics } from "./DashboardMetrics";
import { resolveDashboardAudience } from "./dashboard-role";
import { buildMetricCards } from "./metric-cards";
import { quickActionsFor } from "./quick-actions";
import { TodaySchedule } from "./TodaySchedule";
import { useOnlineBookingToasts } from "./useOnlineBookingToasts";
import { DAY_PAGE_DEFAULT, DAY_PAGE_SIZES, type Summary } from "./types";

const POLL_MS = 30_000;

export function DashboardView() {
  const { can, status, me } = useSession();
  const [refresh, setRefresh] = useState(0);
  const [activeFilter, setActiveFilter] = useState<string>("today");
  const [pageSize, setPageSize] = useState<(typeof DAY_PAGE_SIZES)[number]>(DAY_PAGE_DEFAULT);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [onlineReview, setOnlineReview] = useState<"all" | "unreviewed" | "reviewed">("all");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [adv, setAdv] = useState({ gender: "", channel: "" });
  const [financeTarget, setFinanceTarget] = useState<FinanceDrawerTarget | null>(null);
  const today = tehranTodayYmd();
  const tomorrow = shiftTehranYmd(today, 1);
  const bounds = tehranDayBoundsUtc(today);
  const range = { start_at_utc: bounds.start, end_at_utc: bounds.end };
  const ready = status === "ready";
  const audience = resolveDashboardAudience(me?.governance_roles ?? [], can);
  const activeFilterCount = [adv.gender, adv.channel, search.trim()].filter(Boolean).length;
  useOnlineBookingToasts(ready && can(P.appointmentsList), refresh);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(search.trim()), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  // Reset page when query context changes (React-recommended render-time adjust).
  const pageContextKey = `${activeFilter}|${debouncedQ}|${pageSize}|${onlineReview}|${adv.gender}|${adv.channel}`;
  const [pageContextSeen, setPageContextSeen] = useState(pageContextKey);
  if (pageContextKey !== pageContextSeen) {
    setPageContextSeen(pageContextKey);
    setOffset(0);
  }

  const summary = useApiQuery<Summary>(
    ready ? `/api/v1/dashboard/summary${buildQuery(range)}` : null,
    "بارگذاری آمار داشبورد ناموفق بود",
    refresh,
  );
  const day = useApiQuery<ManagementResponse & { metric?: string; total: number }>(
    ready && can(P.appointmentsList)
      ? `/api/v1/dashboard/day${buildQuery({
          ...range,
          metric: activeFilter,
          q: debouncedQ || undefined,
          limit: pageSize,
          offset,
          online_review: activeFilter === "online" && onlineReview !== "all" ? onlineReview : undefined,
          booking_channel: adv.channel || undefined,
        })}`
      : null,
    "بارگذاری نوبت‌های امروز ناموفق بود",
    refresh,
    { keepPrevious: true },
  );

  const bump = useCallback(() => setRefresh((value) => value + 1), []);

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
    const onOnline = () => bump();
    schedule();
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("focus", onFocus);
    window.addEventListener("online", onOnline);
    return () => {
      if (timer) window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVis);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("online", onOnline);
    };
  }, [ready, bump]);

  if (status === "loading") return <PageSkeleton />;
  const loading = summary.loading;
  const data = summary.data;
  const cards = buildMetricCards(audience, can, today, tomorrow, data).map((card) => ({
    ...card,
        onActivate:
      card.interactive === false
        ? undefined
        : audience.composition === "operational" && card.href.startsWith("#dash-")
          ? () => {
              setActiveFilter(card.href.replace("#dash-", ""));
              setOffset(0);
            }
          : undefined,
  }));
  const actions = quickActionsFor(audience).filter((item) => item.allowed(can));
  const nothingToShow = !loading && cards.length === 0 && actions.length === 0 && !can(P.appointmentsList);

  function clearMetric() {
    setActiveFilter("today");
    setOnlineReview("all");
  }

  function clearAll() {
    clearMetric();
    setSearch("");
    setDebouncedQ("");
    setAdv({ gender: "", channel: "" });
    setOffset(0);
  }

  return (
    <main className="space-y-3" data-testid="dashboard-page" data-dashboard={audience.composition}>
      <PageHeader title={audience.composition === "management" ? "داشبورد مدیریت" : "میز کار پذیرش"} />

      {summary.error ? <Alert testId="dashboard-error">{summary.error.message}</Alert> : null}

      <DashboardMetrics
        cards={cards}
        loading={loading}
        activeKey={activeFilter}
        onSelect={(key) => {
          if (key === "today") {
            clearMetric();
            return;
          }
          setActiveFilter(key === activeFilter ? "today" : key);
        }}
      />

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

      {can(P.appointmentsList) ? (
        <TodaySchedule
          today={today}
          query={day}
          can={can}
          filterKey={activeFilter}
          filterLabel={METRIC_FILTER_LABELS[activeFilter] || "نوبت‌های امروز"}
          search={search}
          onSearchChange={setSearch}
          pageSize={pageSize}
          onPageSizeChange={(size) => setPageSize(size as (typeof DAY_PAGE_SIZES)[number])}
          offset={offset}
          onOffsetChange={setOffset}
          total={day.data?.total ?? 0}
          onOpenFinance={setFinanceTarget}
          filtersOpen={filtersOpen}
          onToggleFilters={() => setFiltersOpen((v) => !v)}
          activeFilterCount={activeFilterCount + (activeFilter !== "today" ? 1 : 0)}
          onClearMetric={activeFilter !== "today" ? clearMetric : undefined}
          onClearAll={clearAll}
          adv={adv}
          onAdvChange={setAdv}
          onlineReview={onlineReview}
          onOnlineReviewChange={setOnlineReview}
          onMutated={bump}
        />
      ) : null}

      {nothingToShow ? (
        <EmptyState icon="info" title="برای حساب شما شاخصی قابل نمایش نیست" description="مجوزهای لازم برای مشاهدهٔ آمار تخصیص داده نشده است." />
      ) : null}

      <AppointmentFinanceDrawer target={financeTarget} onClose={() => setFinanceTarget(null)} />
    </main>
  );
}
