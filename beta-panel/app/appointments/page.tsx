"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, formatApiError, formatTehran, type ApiErrorBody } from "@/lib/client";

type AppointmentItem = {
  appointment_id: string;
  patient_first_name: string;
  patient_last_name: string;
  service_name: string;
  status: string;
  scheduled_start_at_utc: string;
  scheduled_end_at_utc: string;
};

function dayBoundsTehran(dateYmd: string): { start: string; end: string } {
  const startLocal = `${dateYmd}T00:00`;
  const endLocal = `${dateYmd}T23:59`;
  // Reuse desk conversion by constructing Date with Tehran offset via Intl.
  const toUtc = (local: string) => {
    const [datePart, timePart] = local.split("T");
    const [y, m, d] = datePart.split("-").map(Number);
    const [hh, mm] = timePart.split(":").map(Number);
    const guess = new Date(Date.UTC(y, m - 1, d, hh, mm, 0));
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Tehran",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    const parts = Object.fromEntries(
      formatter.formatToParts(guess).map((p) => [p.type, p.value]),
    );
    const asTehran = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour) % 24,
      Number(parts.minute),
      Number(parts.second),
    );
    return new Date(guess.getTime() - (asTehran - guess.getTime())).toISOString();
  };
  const start = toUtc(startLocal);
  const endDate = new Date(toUtc(endLocal));
  endDate.setUTCMinutes(endDate.getUTCMinutes() + 1);
  return { start, end: endDate.toISOString() };
}

export default function AppointmentsPage() {
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [items, setItems] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      const me = await apiFetch("/api/auth/me");
      if (me.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const { start, end } = dayBoundsTehran(date);
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
      if (!response.ok) {
        setError(formatApiError(data, "بارگذاری نوبت‌ها ناموفق بود"));
        setItems([]);
        setLoading(false);
        return;
      }
      setItems(data.items || []);
      setLoading(false);
    }
    void load();
  }, [date, router]);

  return (
    <main className="space-y-6 animate-rise">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-sea-deep)]">نوبت‌های روز</h1>
          <p className="text-[var(--color-ink)]/70">فهرست واقعی از PostgreSQL — زمان‌ها به وقت تهران</p>
        </div>
        <label className="space-y-1 text-sm">
          <span className="block">تاریخ</span>
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
