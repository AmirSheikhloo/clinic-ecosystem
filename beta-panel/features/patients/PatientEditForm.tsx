"use client";

import { useState, type FormEvent } from "react";
import { Alert } from "@/components/feedback/Alert";
import { JalaliDateField } from "@/components/forms/jalali/JalaliDateField";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiJson, type ApiFail } from "@/lib/api";
import { tehranTodayYmd } from "@/lib/tehran";
import type { PatientRow } from "./types";

type Props = {
  patient: PatientRow;
  canUpdate: boolean;
  onSaved: (row: PatientRow, message: string) => void;
  onStale: () => void;
};

export function PatientEditForm({ patient, canUpdate, onSaved, onStale }: Props) {
  const [firstName, setFirstName] = useState(patient.first_name);
  const [lastName, setLastName] = useState(patient.last_name);
  const [birthDate, setBirthDate] = useState(patient.birth_date ?? "");
  const [dossier, setDossier] = useState(patient.dossier_number ?? "");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy || !canUpdate) return;
    setBusy(true);
    setFailure(null);
    const result = await apiJson<PatientRow>(`/api/v1/patients/${patient.patient_profile_id}`, {
      method: "PATCH",
      version: patient.aggregate_version,
      body: {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        birth_date: birthDate || null,
        dossier_number: dossier.trim() || null,
      },
      fallbackMessage: "ذخیرهٔ تغییرات ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    onSaved(result.data, "اطلاعات بیمار به‌روزرسانی شد");
  }

  const stale = failure?.status === 412;

  return (
    <Card>
      <form onSubmit={save} className="space-y-3" data-testid="patient-edit-form">
        <h2 className="ds-section-title">اطلاعات اداری</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label="نام" value={firstName} onChange={(e) => setFirstName(e.target.value)} required disabled={!canUpdate} maxLength={120} data-testid="patient-first-name" />
          <TextField label="نام خانوادگی" value={lastName} onChange={(e) => setLastName(e.target.value)} required disabled={!canUpdate} maxLength={120} data-testid="patient-last-name" />
          <JalaliDateField label="تاریخ تولد" value={birthDate} onChange={setBirthDate} max={tehranTodayYmd()} disabled={!canUpdate} testId="patient-birth-date" allowClear />
          <TextField label="شماره پرونده" value={dossier} onChange={(e) => setDossier(e.target.value)} disabled={!canUpdate} maxLength={64} data-testid="patient-dossier" />
        </div>
        <p className="ds-hint">تلفن و شناسهٔ رسمی هنوز در این نسخه پشتیبانی نمی‌شود و پروندهٔ بالینی در این بخش وجود ندارد.</p>
        {failure && (
          <div className="space-y-2" data-testid="patient-edit-error">
            <Alert>{stale ? "این پرونده در این فاصله توسط کاربر دیگری تغییر کرده است." : failure.message}</Alert>
            {stale && (
              <Button variant="ghost" onClick={onStale} data-testid="patient-reload">
                بارگذاری مجدد آخرین نسخه
              </Button>
            )}
          </div>
        )}
        {canUpdate ? (
          <Button type="submit" loading={busy} data-testid="patient-save">
            {busy ? "در حال ذخیره…" : "ذخیره تغییرات"}
          </Button>
        ) : (
          <p className="text-sm text-[var(--ds-text-muted)]">شما مجوز ویرایش اطلاعات بیمار را ندارید.</p>
        )}
      </form>
    </Card>
  );
}
