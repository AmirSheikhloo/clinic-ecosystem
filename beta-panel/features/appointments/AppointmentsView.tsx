"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import {
  apiFetch,
  formatApiError,
  tehranDayBoundsUtc,
  tehranTodayYmd,
  type ApiErrorBody,
} from "@/lib/client";
import { AppointmentTable } from "./AppointmentTable";
import { DayTimeline } from "./DayTimeline";
import { DayToolbar } from "./DayToolbar";
import type { AppointmentItem, SortKey } from "./types";

export function AppointmentsView() {
  const router = useRouter();
  const [date, setDate] = useState(() => tehranTodayYmd());
  const [items, setItems] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("time");
  const [statusFilter, setStatusFilter] = useState("ALL");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const me = await apiFetch("/api/auth/me");
        if (me.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        const { start, end } = tehranDayBoundsUtc(date);
        const response = await apiFetch(
          `/api/appointments?start_at_utc=${encodeURIComponent(start)}&end_at_utc=${encodeURIComponent(end)}`,
        );
        if (response.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        const data = (await response.json().catch(() => ({}))) as ApiErrorBody & {
          items?: AppointmentItem[];
        };
        if (cancelled) return;
        if (!response.ok) {
          setError(formatApiError(data, "بارگذاری نوبت‌ها ناموفق بود"));
          setItems([]);
          return;
        }
        setItems(data.items || []);
      } catch {
        if (!cancelled) {
          setError("ارتباط برای بارگذاری نوبت‌ها برقرار نشد");
          setItems([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [date, router]);

  const statuses = useMemo(
    () => Array.from(new Set(items.map((item) => item.status))).sort(),
    [items],
  );

  const visible = useMemo(() => {
    const filtered =
      statusFilter === "ALL"
        ? items
        : items.filter((item) => item.status === statusFilter);
    return filtered.slice().sort((a, b) => {
      if (sortKey === "patient") {
        return `${a.patient_first_name}${a.patient_last_name}`.localeCompare(
          `${b.patient_first_name}${b.patient_last_name}`,
          "fa",
        );
      }
      if (sortKey === "service") {
        return a.service_name.localeCompare(b.service_name, "fa");
      }
      return a.scheduled_start_at_utc.localeCompare(b.scheduled_start_at_utc);
    });
  }, [items, sortKey, statusFilter]);

  return (
    <main className="space-y-6 animate-rise" data-testid="appointments-page">
      <DayToolbar
        date={date}
        onDateChange={setDate}
        visibleCount={visible.length}
        sortKey={sortKey}
        onSortKeyChange={setSortKey}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statuses={statuses}
      />

      {loading && <p className="text-[var(--ds-text-muted)]">در حال بارگذاری…</p>}
      {error && <Alert>{error}</Alert>}
      {!loading && !error && visible.length === 0 && (
        <EmptyState title="نوبتی برای این تاریخ ثبت نشده است" />
      )}

      {!loading && visible.length > 0 && (
        <>
          <AppointmentTable items={visible} />
          <DayTimeline items={visible} />
        </>
      )}
    </main>
  );
}
