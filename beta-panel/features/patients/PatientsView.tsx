"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert } from "@/components/feedback/Alert";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import type { Patient } from "@/features/reception/types";
import { PatientRegisterForm } from "./PatientRegisterForm";
import { PatientSearchList } from "./PatientSearchList";

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
      setPatients((prev) => [
        data,
        ...prev.filter((p) => p.patient_profile_id !== data.patient_profile_id),
      ]);
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
        <PatientSearchList
          query={query}
          onQueryChange={setQuery}
          onSearch={search}
          patients={patients}
          selected={selected}
          onSelect={setSelected}
        />
        <PatientRegisterForm
          firstName={firstName}
          lastName={lastName}
          birthDate={birthDate}
          onFirstNameChange={setFirstName}
          onLastNameChange={setLastName}
          onBirthDateChange={setBirthDate}
          busy={busy}
          onRegister={register}
          selected={selected}
        />
      </section>

      {message && (
        <Alert tone="ok" testId="patients-status">
          {message}
        </Alert>
      )}
      {error && <Alert testId="patients-error">{error}</Alert>}
    </main>
  );
}
