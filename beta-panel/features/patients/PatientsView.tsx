"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { Alert } from "@/components/feedback/Alert";
import { useToast } from "@/components/feedback/Toast";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { apiJson } from "@/lib/api";
import { P } from "@/lib/permissions";
import { PatientDirectory } from "./PatientDirectory";
import { PatientRegisterForm } from "./PatientRegisterForm";
import type { PatientRow } from "./types";

type Registered = Pick<PatientRow, "patient_profile_id" | "first_name" | "last_name">;

export function PatientsView() {
  const { status, can } = useSession();
  const toast = useToast();
  const [registered, setRegistered] = useState<Registered | null>(null);
  const params = useSearchParams();
  const [formOpen, setFormOpen] = useState(() => params.get("register") === "1");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [nationalId, setNationalId] = useState("");
  const [identityExceptionReason, setIdentityExceptionReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);

  async function register(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    const result = await apiJson<Registered>("/api/patients", {
      method: "POST",
      body: {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        birth_date: birthDate || null,
        national_id: nationalId.trim() || null,
        identity_exception_reason: nationalId.trim() ? null : (identityExceptionReason.trim() || null),
      },
      fallbackMessage: "ثبت بیمار ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      toast.failure(result.message);
      return;
    }
    setRegistered(result.data);
    toast.success("بیمار با موفقیت ثبت شد");
    setFirstName("");
    setLastName("");
    setBirthDate("");
    setNationalId("");
    setIdentityExceptionReason("");
    setFormOpen(false);
    setRefreshToken((value) => value + 1);
  }

  if (status === "loading") return <PageSkeleton />;
  if (status === "error") return <Alert>نشست معتبر نیست</Alert>;
  if (!can(P.patientsSearch) && !can(P.patientsRegister)) return <AccessDenied what="مدیریت بیماران" />;

  return (
    <main className="space-y-5" data-testid="patients-page">
      <PageHeader
        title="بیماران"
        description="فهرست، جستجو، ثبت و پروندهٔ اداری بیماران. اطلاعات بالینی در این بخش نگهداری نمی‌شود."
        actions={
          can(P.patientsRegister) ? (
            <Button icon="plus" onClick={() => { setError(null); setFormOpen(true); }} data-testid="patients-new">
              بیمار جدید
            </Button>
          ) : null
        }
      />

      {registered ? (
        <Alert tone="ok" testId="patients-status">
          <p className="font-medium">بیمار ثبت شد: <span data-testid="patients-selected">{registered.first_name} {registered.last_name}</span></p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Link href={`/desk?patient=${encodeURIComponent(registered.patient_profile_id)}`} className="ds-btn ds-btn-primary ds-btn-sm" data-testid="patients-to-desk">
              ادامه در میز پذیرش
            </Link>
            {can(P.patientsViewProfile) ? (
              <Link href={`/patients/${encodeURIComponent(registered.patient_profile_id)}`} className="ds-btn ds-btn-ghost ds-btn-sm" data-testid="patients-to-profile">
                مشاهدهٔ پرونده
              </Link>
            ) : null}
          </div>
        </Alert>
      ) : null}

      {can(P.patientsSearch) ? <PatientDirectory refreshToken={refreshToken} /> : <AccessDenied what="مشاهدهٔ فهرست بیماران" />}

      <Dialog open={formOpen} placement="drawer" title="ثبت بیمار جدید" description="اطلاعات هویتی اولیهٔ بیمار را وارد کنید." onClose={() => !busy && setFormOpen(false)} testId="patients-register-dialog">
        {error ? <div className="mb-3"><Alert testId="patients-error">{error}</Alert></div> : null}
        <PatientRegisterForm
          firstName={firstName}
          lastName={lastName}
          birthDate={birthDate}
          nationalId={nationalId}
          identityExceptionReason={identityExceptionReason}
          onFirstNameChange={setFirstName}
          onLastNameChange={setLastName}
          onBirthDateChange={setBirthDate}
          onNationalIdChange={setNationalId}
          onIdentityExceptionReasonChange={setIdentityExceptionReason}
          busy={busy}
          onRegister={register}
          onCancel={() => setFormOpen(false)}
        />
      </Dialog>
    </main>
  );
}
