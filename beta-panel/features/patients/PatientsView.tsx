"use client";

import { FormEvent, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { useToast } from "@/components/feedback/Toast";
import { PageHeader } from "@/components/ui/PageHeader";
import { useSession } from "@/components/session/SessionProvider";
import { apiJson } from "@/lib/api";
import { P } from "@/lib/permissions";
import { PatientDirectory } from "./PatientDirectory";
import { PatientRegisterForm } from "./PatientRegisterForm";
import type { PatientRow } from "./types";

type Selected = Pick<PatientRow, "patient_profile_id" | "first_name" | "last_name">;

export function PatientsView() {
  const { status, can } = useSession();
  const toast = useToast();
  const [selected, setSelected] = useState<Selected | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);

  async function register(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    const result = await apiJson<Selected>("/api/patients", {
      method: "POST",
      body: {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        birth_date: birthDate || null,
      },
      fallbackMessage: "ثبت بیمار ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      toast.failure(result.message);
      return;
    }
    setSelected(result.data);
    setMessage(`بیمار ثبت شد — شناسه پروفایل: ${result.data.patient_profile_id}`);
    toast.success("بیمار با موفقیت ثبت شد");
    setFirstName("");
    setLastName("");
    setBirthDate("");
    setRefreshToken((value) => value + 1);
  }

  if (status === "loading") {
    return <p className="text-[var(--ds-text-muted)]">در حال آماده‌سازی…</p>;
  }
  if (status === "error") return <Alert>نشست معتبر نیست</Alert>;
  if (!can(P.patientsSearch) && !can(P.patientsRegister)) {
    return <AccessDenied what="مدیریت بیماران" />;
  }

  return (
    <main className="space-y-6 animate-rise" data-testid="patients-page">
      <PageHeader
        title="فضای بیماران"
        description="فهرست، جستجو، ثبت و پرونده اداری بیماران — بدون داده بالینی؛ داده مصنوعی"
      />
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        {can(P.patientsSearch) ? (
          <PatientDirectory
            selectedId={selected?.patient_profile_id ?? null}
            onSelect={setSelected}
            refreshToken={refreshToken}
          />
        ) : (
          <AccessDenied what="مشاهدهٔ فهرست بیماران" />
        )}
        {can(P.patientsRegister) && (
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
            canOpenProfile={can(P.patientsViewProfile)}
          />
        )}
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
