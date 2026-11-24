"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import { formatJalaliDate } from "@/lib/format/jalali";

type Patient = {
  patient_profile_id: string;
  person_id: string;
  first_name: string;
  last_name: string;
  birth_date: string | null;
};

export function PatientsView() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selected, setSelected] = useState<Patient | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      const me = await apiFetch("/api/auth/me");
      if (cancelled) return;
      if (me.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      setReady(me.ok);
      if (!me.ok) setError("نشست معتبر نیست");
    }
    void boot().catch(() => {
      if (!cancelled) setError("ارتباط برای آماده‌سازی برقرار نشد");
    });
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function search() {
    setError(null);
    try {
      const response = await apiFetch(`/api/patients?q=${encodeURIComponent(query.trim())}`);
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & {
        items?: Patient[];
      };
      if (!response.ok) {
        setError(formatApiError(data, "جستجوی بیمار ناموفق بود"));
        return;
      }
      setPatients(data.items || []);
    } catch {
      setError("ارتباط برای جستجوی بیمار برقرار نشد");
    }
  }

  async function register(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await apiFetch("/api/patients", {
        method: "POST",
        csrf: true,
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          birth_date: birthDate || null,
        }),
      });
      if (response.status === 401) {
        router.replace("/login?expired=1");
        return;
      }
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody & Patient;
      if (!response.ok) {
        setError(formatApiError(data, "ثبت بیمار ناموفق بود"));
        return;
      }
      setSelected(data);
      setPatients((prev) => [data, ...prev.filter((p) => p.patient_profile_id !== data.patient_profile_id)]);
      setMessage(`بیمار ثبت شد — شناسه پروفایل: ${data.patient_profile_id}`);
      setFirstName("");
      setLastName("");
      setBirthDate("");
    } catch {
      setError("ارتباط برای ثبت بیمار برقرار نشد");
    } finally {
      setBusy(false);
    }
  }

  if (!ready && !error) {
    return <p className="text-[var(--ds-text-muted)]">در حال آماده‌سازی…</p>;
  }

  return (
    <main className="space-y-6 animate-rise" data-testid="patients-page">
      <header>
        <h2 className="text-2xl font-bold text-[var(--ds-primary-strong)]">فضای بیماران</h2>
        <p className="text-[var(--ds-text-muted)]">
          جستجو و ثبت مصنوعی — فقط قراردادهای API موجود؛ بدون پرونده بالینی جعلی
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-4">
          <h3 className="font-semibold">جستجو</h3>
          <div className="flex gap-2">
            <input
              className="ds-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="نام یا نام خانوادگی"
              data-testid="patients-search-query"
            />
            <Button onClick={search}>جستجو</Button>
          </div>
          <ul className="max-h-72 space-y-2 overflow-auto">
            {patients.map((patient) => (
              <li key={patient.patient_profile_id}>
                <button
                  type="button"
                  className={`w-full rounded-[var(--ds-radius-md)] border px-3 py-2 text-right transition-colors duration-[var(--ds-motion-micro)] ${
                    selected?.patient_profile_id === patient.patient_profile_id
                      ? "border-[var(--ds-primary)] bg-[var(--ds-surface-muted)]"
                      : "border-[var(--ds-border)] hover:bg-[var(--ds-surface-muted)]"
                  }`}
                  onClick={() => setSelected(patient)}
                >
                  <span className="font-medium">
                    {patient.first_name} {patient.last_name}
                  </span>
                  <span className="mt-1 block text-xs text-[var(--ds-text-muted)]">
                    پروفایل: {patient.patient_profile_id}
                  </span>
                  {patient.birth_date && (
                    <span className="mt-1 block text-xs text-[var(--ds-text-muted)] tabular-nums">
                      تولد (جلالی نمایشی): {formatJalaliDate(`${patient.birth_date}T12:00:00Z`)}
                    </span>
                  )}
                </button>
              </li>
            ))}
            {!patients.length && (
              <EmptyState title="نتیجه‌ای نیست" description="برای فهرست کامل، API جستجو با پارامتر q الزامی است." />
            )}
          </ul>
        </Card>

        <Card>
          <form onSubmit={register} className="space-y-3">
            <h3 className="font-semibold">ثبت بیمار مصنوعی</h3>
            <div className="grid grid-cols-2 gap-2">
              <input
                className="ds-input"
                placeholder="نام"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
              <input
                className="ds-input"
                placeholder="نام خانوادگی"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
            <label className="block space-y-1 text-sm">
              <span>تاریخ تولد (ورودی تقویمی استاندارد مرورگر)</span>
              <input
                type="date"
                className="ds-input"
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
              />
            </label>
            <Button type="submit" disabled={busy}>
              {busy ? "در حال ثبت…" : "ثبت بیمار"}
            </Button>
          </form>
          {selected && (
            <div className="mt-6 space-y-3 border-t border-[var(--ds-border)] pt-4">
              <p className="text-sm">
                انتخاب‌شده: {selected.first_name} {selected.last_name}
              </p>
              <Link
                href="/desk"
                className="ds-btn ds-btn-primary"
                onClick={() => {
                  try {
                    sessionStorage.setItem(
                      "ce_beta_selected_patient",
                      JSON.stringify(selected),
                    );
                  } catch {
                    /* optional handoff only */
                  }
                }}
              >
                ادامه در میز پذیرش
              </Link>
            </div>
          )}
        </Card>
      </section>

      {message && <Alert tone="ok">{message}</Alert>}
      {error && <Alert>{error}</Alert>}
    </main>
  );
}
