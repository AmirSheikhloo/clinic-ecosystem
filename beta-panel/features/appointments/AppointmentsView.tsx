"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import {
  apiFetch,
  formatApiError,
  formatTehran,
  shiftTehranYmd,
  tehranDayBoundsUtc,
  tehranTodayYmd,
  type ApiErrorBody,
} from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";
import { formatJalaliFromTehranYmd, formatTehranTime } from "@/lib/format/jalali";
import { appointmentStatusLabel } from "@/lib/format/status";

type AppointmentItem = {
  appointment_id: string;
  patient_first_name: string;
  patient_last_name: string;
  service_name: string;
  status: string;
  scheduled_start_at_utc: string;
  scheduled_end_at_utc: string;
};

type SortKey = "time" | "patient" | "service";

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
    const sorted = filtered.slice().sort((a, b) => {
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
    return sorted;
  }, [items, sortKey, statusFilter]);

  const timelineHours = useMemo(() => {
    const hours: { hour: number; slots: AppointmentItem[] }[] = [];
    for (let hour = 8; hour <= 20; hour += 1) {
      hours.push({
        hour,
        slots: visible.filter((item) => {
          const local = formatTehranTime(item.scheduled_start_at_utc);
          const hh = Number(local.slice(0, 2));
          return hh === hour;
        }),
      });
    }
    return hours;
  }, [visible]);

  return (
    <main className="space-y-6 animate-rise" data-testid="appointments-page">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[var(--ds-primary-strong)]">نوبت‌های روز</h2>
          <p className="text-[var(--ds-text-muted)]">
            جلالی با ارقام لاتین — {formatJalaliFromTehranYmd(date)} · تعداد:{" "}
            <span className="tabular-nums">{formatCount(visible.length)}</span>
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <Button variant="ghost" onClick={() => setDate(tehranTodayYmd())}>
            امروز
          </Button>
          <Button variant="ghost" onClick={() => setDate((d) => shiftTehranYmd(d, -1))}>
            روز قبل
          </Button>
          <Button variant="ghost" onClick={() => setDate((d) => shiftTehranYmd(d, 1))}>
            روز بعد
          </Button>
          <label className="space-y-1 text-sm">
            <span className="block">تاریخ (مرز تهران)</span>
            <input
              type="date"
              data-testid="appointments-date"
              className="ds-input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
        </div>
      </header>

      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          مرتب‌سازی
          <select
            className="ds-input mt-1"
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
          >
            <option value="time">زمان</option>
            <option value="patient">بیمار</option>
            <option value="service">خدمت</option>
          </select>
        </label>
        <label className="text-sm">
          وضعیت
          <select
            className="ds-input mt-1"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">همه</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {appointmentStatusLabel(status)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p className="text-[var(--ds-text-muted)]">در حال بارگذاری…</p>}
      {error && <Alert>{error}</Alert>}
      {!loading && !error && visible.length === 0 && (
        <EmptyState title="نوبتی برای این تاریخ ثبت نشده است" />
      )}

      {!loading && visible.length > 0 && (
        <>
          <Card className="overflow-x-auto p-0">
            <table className="min-w-full text-sm">
              <thead className="bg-[var(--ds-surface-muted)] text-[var(--ds-text-muted)]">
                <tr>
                  <th className="px-4 py-3 text-right font-medium">زمان</th>
                  <th className="px-4 py-3 text-right font-medium">بیمار</th>
                  <th className="px-4 py-3 text-right font-medium">خدمت</th>
                  <th className="px-4 py-3 text-right font-medium">وضعیت</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((item) => (
                  <tr
                    key={item.appointment_id}
                    className="border-t border-[var(--ds-border)]"
                    data-testid="appointment-row"
                    data-appointment-id={item.appointment_id}
                  >
                    <td className="px-4 py-3 tabular-nums">{formatTehran(item.scheduled_start_at_utc)}</td>
                    <td className="px-4 py-3">
                      {item.patient_first_name} {item.patient_last_name}
                    </td>
                    <td className="px-4 py-3">{item.service_name}</td>
                    <td className="px-4 py-3">{appointmentStatusLabel(item.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card>
            <h3 className="mb-3 font-semibold">جدول زمانی روزانه</h3>
            <div className="space-y-2">
              {timelineHours.map(({ hour, slots }) => (
                <div
                  key={hour}
                  className="grid grid-cols-[4rem_1fr] gap-3 border-b border-[var(--ds-border)] py-2 last:border-0"
                >
                  <div className="tabular-nums text-sm text-[var(--ds-text-muted)]">
                    {String(hour).padStart(2, "0")}:00
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {!slots.length && (
                      <span className="text-xs text-[var(--ds-text-muted)]">—</span>
                    )}
                    {slots.map((slot) => (
                      <span
                        key={slot.appointment_id}
                        className="rounded-md bg-[var(--ds-surface-muted)] px-2 py-1 text-xs"
                      >
                        {formatTehranTime(slot.scheduled_start_at_utc)} · {slot.patient_first_name}{" "}
                        {slot.patient_last_name}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </main>
  );
}
