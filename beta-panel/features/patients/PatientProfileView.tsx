"use client";

import Link from "next/link";
import { useState } from "react";
import { AccessDenied } from "@/components/feedback/AccessDenied";
import { Alert } from "@/components/feedback/Alert";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { useSession } from "@/components/session/SessionProvider";
import { apiJson } from "@/lib/api";
import { formatJalaliDate, formatJalaliFromTehranYmd } from "@/lib/format/jalali";
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
  const [confirming, setConfirming] = useState(false);
  const allowed = can(P.patientsViewProfile);
  const query = useApiQuery<PatientRow>(allowed ? `/api/v1/patients/${patientId}` : null, "بارگذاری پرونده ناموفق بود");

  if (status === "loading") return <PageSkeleton />;
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
    setConfirming(false);
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
    <main className="space-y-6 " data-testid="patient-profile-page">
      <QueryBoundary loading={query.loading && !patient} error={query.error} deniedWhat="مشاهدهٔ پروندهٔ بیمار" onRetry={query.reload}>
        {patient && (
          <>
            <PageHeader
              title={`${patient.first_name} ${patient.last_name}`}
              description={
                <span className="inline-flex flex-wrap items-center gap-x-4 gap-y-1">
                  <ActiveBadge active={patient.is_active} />
                  <span className="tabular-nums">شماره پرونده: {patient.dossier_number ?? "—"}</span>
                  <span className="tabular-nums">تاریخ تولد: {patient.birth_date ? formatJalaliFromTehranYmd(patient.birth_date) : "ثبت نشده"}</span>
                  <span className="tabular-nums">ثبت: {formatJalaliDate(patient.created_at_utc)}</span>
                </span>
              }
              actions={
                <>
                  <Link href="/patients" className="ds-btn ds-btn-ghost">فهرست بیماران</Link>
                  {can(P.appointmentsList) && (
                    <Link href="/appointments" className="ds-btn ds-btn-ghost" data-testid="patient-calendar">تقویم نوبت‌ها</Link>
                  )}
                  {patient.is_active && can(P.appointmentsSchedule) && (
                    <Link href={`/desk?patient=${patient.patient_profile_id}`} className="ds-btn ds-btn-primary" data-testid="patient-book">
                      نوبت‌دهی در میز پذیرش
                    </Link>
                  )}
                  {can(P.patientsSetActive) && (
                    <Button variant={patient.is_active ? "danger" : "ghost"} onClick={() => setConfirming(true)} data-testid="patient-toggle-active">
                      {patient.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
                    </Button>
                  )}
                </>
              }
            />
            <ConfirmDialog
              open={confirming}
              title={patient.is_active ? "غیرفعال‌سازی بیمار" : "فعال‌سازی بیمار"}
              confirmLabel={patient.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
              tone={patient.is_active ? "danger" : "primary"}
              busy={busy}
              testId="patient-toggle-dialog"
              onCancel={() => setConfirming(false)}
              onConfirm={() => void toggleActive(patient)}
            >
              <p>
                {patient.is_active
                  ? `«${patient.first_name} ${patient.last_name}» از فهرست پیش‌فرض بیماران و نوبت‌دهی جدید کنار گذاشته می‌شود؛ سابقهٔ پرونده و نوبت‌های قبلی حفظ می‌شود.`
                  : `«${patient.first_name} ${patient.last_name}» دوباره در فهرست بیماران فعال و نوبت‌دهی قرار می‌گیرد.`}
              </p>
            </ConfirmDialog>
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
