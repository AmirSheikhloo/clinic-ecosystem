"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { useSession } from "@/components/session/SessionProvider";
import { buildQuery } from "@/lib/api";
import { rangeBoundsUtc, visibleRange, type CalendarView } from "@/lib/calendar/jalali-grid";
import { tehranTodayYmd } from "@/lib/client";
import { P } from "@/lib/permissions";
import { CATALOG_CACHE_MS } from "@/lib/query-cache";
import { useApiQuery } from "@/lib/use-api-query";
import { AppointmentDetailsDialog } from "./AppointmentDetailsDialog";
import { AppointmentTable } from "./AppointmentTable";
import { groupByTehranDay, rangeDays, sortAppointments } from "./calendar-model";
import { CalendarToolbar, type CalendarFilters, type Option } from "./CalendarToolbar";
import { DayTimeline } from "./DayTimeline";
import { MonthView } from "./MonthView";
import { WeekView } from "./WeekView";
import { CALENDAR_LIMIT, CALENDAR_STATUSES, type CalendarResponse, type SortKey } from "./types";

type ServiceDto = { id: string; service_name: string };
type ResourceDto = { id: string; resource_name: string };

export function AppointmentsView() {
  const { can, status } = useSession();
  const params = useSearchParams();
  const requestedDate = params.get("date");
  const requestedView = params.get("view");
  const requestedStatus = params.get("status") ?? "";
  const [view, setView] = useState<CalendarView>(() =>
    requestedView === "week" || requestedView === "month" ? requestedView : "day",
  );
  const [anchor, setAnchor] = useState(() =>
    requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate) ? requestedDate : tehranTodayYmd(),
  );
  const [filters, setFilters] = useState<CalendarFilters>({
    serviceId: "",
    resourceId: "",
    status: (CALENDAR_STATUSES as readonly string[]).includes(requestedStatus) ? requestedStatus : "",
  });
  const [sortKey, setSortKey] = useState<SortKey>("time");
  const [openId, setOpenId] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const allowed = can(P.appointmentsList);

  const range = useMemo(() => visibleRange(view, anchor), [view, anchor]);
  const path = useMemo(() => {
    const { start, end } = rangeBoundsUtc(range);
    return `/api/v1/appointments/calendar${buildQuery({
      start_at_utc: start,
      end_at_utc: end,
      service_id: filters.serviceId,
      resource_id: filters.resourceId,
      status: filters.status,
      limit: CALENDAR_LIMIT,
    })}`;
  }, [range, filters]);

  const calendar = useApiQuery<CalendarResponse>(allowed ? path : null, "بارگذاری نوبت‌ها ناموفق بود", refresh);
  const services = useApiQuery<{ items: ServiceDto[] }>(allowed && can(P.catalogServicesRead) ? "/api/catalog/services" : null, undefined, 0, { cacheMs: CATALOG_CACHE_MS });
  const resources = useApiQuery<{ items: ResourceDto[] }>(allowed && can(P.resourcesRead) ? "/api/catalog/resources" : null, undefined, 0, { cacheMs: CATALOG_CACHE_MS });

  const items = calendar.data?.items;
  const groups = useMemo(() => groupByTehranDay(items ?? []), [items]);
  const dayItems = useMemo(() => sortAppointments(items ?? [], sortKey), [items, sortKey]);
  const serviceOptions: Option[] = (services.data?.items ?? []).map((s) => ({ id: s.id, label: s.service_name }));
  const resourceOptions: Option[] = (resources.data?.items ?? []).map((r) => ({ id: r.id, label: r.resource_name }));
  const canOpen = can(P.appointmentsDetails);
  const open = (item: { appointment_id: string }) => setOpenId(item.appointment_id);

  if (status === "loading") return <PageSkeleton />;
  if (!allowed) return <AccessDenied what="مشاهدهٔ نوبت‌ها" />;

  return (
    <main className="space-y-5" data-testid="appointments-page">
      <CalendarToolbar
        view={view}
        onViewChange={setView}
        anchor={anchor}
        onAnchorChange={setAnchor}
        count={items ? items.length : null}
        loading={calendar.loading}
        onRefresh={() => setRefresh((v) => v + 1)}
        filters={filters}
        onFiltersChange={setFilters}
        services={serviceOptions}
        resources={resourceOptions}
        sortKey={sortKey}
        onSortKeyChange={setSortKey}
      />
      <QueryBoundary loading={calendar.loading && !calendar.data} error={calendar.error} deniedWhat="مشاهدهٔ نوبت‌ها" onRetry={calendar.reload}>
        {calendar.data?.truncated && (
          <Alert tone="danger" testId="calendar-truncated">
            تعداد نوبت‌ها از سقف نمایش ({CALENDAR_LIMIT}) بیشتر است؛ بازهٔ زمانی یا فیلترها را محدودتر کنید.
          </Alert>
        )}
        {calendar.data && view === "day" && (
          dayItems.length === 0 ? (
            <EmptyState
              icon="calendar"
              title="نوبتی برای این تاریخ ثبت نشده است"
              description="فیلترها را بررسی کنید یا از میز پذیرش نوبت دستی ثبت کنید."
              action={<Link href="/desk" className="ds-btn ds-btn-primary">رفتن به میز پذیرش</Link>}
            />
          ) : (
            <>
              <AppointmentTable items={dayItems} onOpen={canOpen ? open : null} />
              <DayTimeline items={dayItems} onOpen={canOpen ? open : null} />
            </>
          )
        )}
        {calendar.data && view === "week" && (
          <WeekView days={rangeDays(range)} groups={groups} todayYmd={tehranTodayYmd()} onOpen={canOpen ? open : null} />
        )}
        {calendar.data && view === "month" && (
          <MonthView
            range={range}
            anchor={anchor}
            groups={groups}
            todayYmd={tehranTodayYmd()}
            onPickDay={(ymd) => {
              setAnchor(ymd);
              setView("day");
            }}
          />
        )}
      </QueryBoundary>
      {openId && (
        <AppointmentDetailsDialog
          appointmentId={openId}
          onClose={() => setOpenId(null)}
          onChanged={() => setRefresh((v) => v + 1)}
        />
      )}
    </main>
  );
}
