"use client";

import Link from "next/link";
import { useState } from "react";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { Alert } from "@/components/feedback/Alert";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { useSession } from "@/components/session/SessionProvider";
import { apiJson } from "@/lib/api";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { PatientEditForm } from "./PatientEditForm";
import { PatientHistory } from "./PatientHistory";
import type { PatientRow } from "./types";

export function PatientProfileView({ patientId }: { patientId: string }) {
  const { can, status } = useSession();
  const toast = useToast();
  const [override, setOverride] = useState<PatientRow | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const allowed = can(P.patientsViewProfile);
  const query = useApiQuery<PatientRow>(allowed ? `/api/v1/patients/${patientId}` : null, "بارگذاری پرونده ناموفق بود");

  if (status === "loading") return <p className="text-[var(--ds-text-muted)]">در حال آماده‌سازی…</p>;
  if (!allowed) return <AccessDenied what="مشاهدهٔ پروندهٔ بیمار" />;

  const patient = override && query.data && override.aggregate_version >= query.data.aggregate_version ? override : query.data;

  async function toggleActive(target: PatientRow) {
    if (busy) return;
    setBusy(true);
    setStatusError(null);
    const result = await apiJson<PatientRow>(`/api/v1/patients/${target.patient_profile_id}`, {
      method: "PATCH",
      version: target.aggregate_version,
      body: { is_active: !target.is_active },
      fallbackMessage: "تغییر وضعیت ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setStatusError(result.status === 412 ? "پرونده توسط کاربر دیگری تغییر کرده است؛ صفحه را تازه کنید." : result.message);
      return;
    }
    setOverride(result.data);
    toast.success(result.data.is_active ? "بیمار فعال شد" : "بیمار غیرفعال شد");
  }

  function reload() {
    setOverride(null);
    setStatusError(null);
    query.reload();
  }

  return (
    <main className="space-y-6 animate-rise" data-testid="patient-profile-page">
      <QueryBoundary loading={query.loading && !patient} error={query.error} deniedWhat="مشاهدهٔ پروندهٔ بیمار" onRetry={query.reload}>
        {patient && (
          <>
            <PageHeader
              title={`${patient.first_name} ${patient.last_name}`}
              description={
                <span className="inline-flex items-center gap-2">
                  <ActiveBadge active={patient.is_active} />
                  <span className="tabular-nums">شماره پرونده: {patient.dossier_number ?? "—"}</span>
                </span>
              }
              actions={
                <>
                  <Link href="/patients" className="ds-btn ds-btn-ghost">بازگشت به فهرست</Link>
                  {patient.is_active && can(P.appointmentsSchedule) && (
                    <Link href={`/desk?patient=${patient.patient_profile_id}`} className="ds-btn ds-btn-primary" data-testid="patient-book">
                      نوبت‌دهی دستی
                    </Link>
                  )}
                  {can(P.patientsSetActive) && (
                    <Button variant="ghost" disabled={busy} onClick={() => void toggleActive(patient)} data-testid="patient-toggle-active">
                      {patient.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
                    </Button>
                  )}
                </>
              }
            />
            {statusError && <Alert testId="patient-status-error">{statusError}</Alert>}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <PatientEditForm
                key={patient.aggregate_version}
                patient={patient}
                canUpdate={can(P.patientsUpdate)}
                onSaved={(row, message) => {
                  setOverride(row);
                  toast.success(message);
                }}
                onStale={reload}
              />
              {can(P.patientsViewHistory) ? <PatientHistory patientId={patientId} /> : <AccessDenied what="مشاهدهٔ سابقهٔ نوبت‌ها" />}
            </div>
          </>
        )}
      </QueryBoundary>
    </main>
  );
}
