"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import {
  apiFetch,
  formatApiError,
  formatTehran,
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

export function DashboardView() {
  const router = useRouter();
  const today = tehranTodayYmd();
  const [items, setItems] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

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
        if (!me.ok) {
          setError("نشست معتبر نیست");
          return;
        }
        const { start, end } = tehranDayBoundsUtc(today);
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
          setError(formatApiError(data, "بارگذاری نوبت‌های امروز ناموفق بود"));
          setItems([]);
          return;
        }
        setItems(data.items || []);
      } catch {
        if (!cancelled) {
          setError("ارتباط برای بارگذاری داشبورد برقرار نشد");
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
  }, [router, today, refreshKey]);

  const upcoming = items
    .slice()
    .sort((a, b) => a.scheduled_start_at_utc.localeCompare(b.scheduled_start_at_utc))
    .slice(0, 8);

  return (
    <main className="space-y-6 animate-rise" data-testid="dashboard-page">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[var(--ds-primary-strong)]">داشبورد پذیرش</h2>
          <p className="text-[var(--ds-text-muted)]">
            آمار روز جاری از پاسخ‌های مجاز سرور — {formatJalaliFromTehranYmd(today)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={() => setRefreshKey((k) => k + 1)}>
            تازه‌سازی
          </Button>
          <Link href="/desk" className="ds-btn ds-btn-primary">
            میز پذیرش
          </Link>
          <Link href="/patients" className="ds-btn ds-btn-ghost">
            ثبت بیمار
          </Link>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-[var(--ds-text-muted)]">نوبت‌های امروز</p>
          <p className="mt-2 text-3xl font-bold tabular-nums" data-testid="dashboard-count">
            {loading ? "…" : formatCount(items.length)}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--ds-text-muted)]">نوبت‌های پیش‌رو (نمایش)</p>
          <p className="mt-2 text-3xl font-bold tabular-nums">
            {loading ? "…" : formatCount(upcoming.length)}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--ds-text-muted)]">محدوده زمانی</p>
          <p className="mt-2 text-sm">Asia/Tehran — فقط داده مجاز API</p>
        </Card>
      </section>

      {loading && <p className="text-[var(--ds-text-muted)]">در حال بارگذاری…</p>}
      {error && <Alert>{error}</Alert>}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="نوبتی برای امروز ثبت نشده است"
          description="از میز پذیرش می‌توانید نوبت دستی ثبت کنید."
        />
      )}
      {!loading && upcoming.length > 0 && (
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
              {upcoming.map((item) => (
                <tr key={item.appointment_id} className="border-t border-[var(--ds-border)]">
                  <td className="px-4 py-3 tabular-nums" title={formatTehran(item.scheduled_start_at_utc)}>
                    {formatTehranTime(item.scheduled_start_at_utc)}
                  </td>
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
      )}
    </main>
  );
}
