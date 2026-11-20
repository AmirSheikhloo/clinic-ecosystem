"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch,
  formatApiError,
  formatTehran,
  tehranDayBoundsUtc,
  tehranTodayYmd,
  type ApiErrorBody,
} from "@/lib/client";

type AppointmentItem = {
  appointment_id: string;
  patient_first_name: string;
  patient_last_name: string;
  service_name: string;
  status: string;
  scheduled_start_at_utc: string;
  scheduled_end_at_utc: string;
};

export default function AppointmentsPage() {
  const router = useRouter();
  const [date, setDate] = useState(() => tehranTodayYmd());
  const [items, setItems] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <main className="space-y-6 animate-rise">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-sea-deep)]">نوبت‌های روز</h1>
          <p className="text-[var(--color-ink)]/70">فهرست واقعی از PostgreSQL — زمان‌ها به وقت تهران</p>
        </div>
        <label className="space-y-1 text-sm">
          <span className="block">تاریخ (تقویم تهران)</span>
          <input
            type="date"
            className="rounded-lg border border-[#c9d5e1] px-3 py-2"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
      </header>

      {loading && <p className="text-[var(--color-ink)]/60">در حال بارگذاری…</p>}
      {error && (
        <p className="rounded-lg bg-red-50 px-4 py-3 text-[var(--color-alert)]" role="alert">
          {error}
        </p>
      )}
      {!loading && !error && items.length === 0 && (
        <p className="rounded-lg border border-dashed border-[#c9d5e1] bg-white/70 px-4 py-8 text-center text-[var(--color-ink)]/60">
          نوبتی برای این تاریخ ثبت نشده است
        </p>
      )}
      {!loading && items.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-[#d7e0ea] bg-white/90">
          <table className="min-w-full text-sm">
            <thead className="bg-[var(--color-mist)] text-[var(--color-ink)]/80">
              <tr>
                <th className="px-4 py-3 text-right font-medium">زمان</th>
                <th className="px-4 py-3 text-right font-medium">بیمار</th>
                <th className="px-4 py-3 text-right font-medium">خدمت</th>
                <th className="px-4 py-3 text-right font-medium">وضعیت</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.appointment_id} className="border-t border-[#e8eef4]">
                  <td className="px-4 py-3">{formatTehran(item.scheduled_start_at_utc)}</td>
                  <td className="px-4 py-3">
                    {item.patient_first_name} {item.patient_last_name}
                  </td>
                  <td className="px-4 py-3">{item.service_name}</td>
                  <td className="px-4 py-3">{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
