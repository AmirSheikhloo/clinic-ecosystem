"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { JalaliDateTimeField } from "@/components/forms/jalali/JalaliDateTimeField";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { apiJson, type ApiFail } from "@/lib/api";
import {
  extractOverlapConflicts,
  formatTehran,
  sortedConflictIds,
  tehranLocalToUtcIso,
  utcIsoToTehranLocal,
  type OverlapConflict,
} from "@/lib/client";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import { OverlapDialog } from "@/features/reception/OverlapDialog";
import { addMinutesIso, durationMinutes } from "./calendar-model";
import { failureMessage } from "./action-errors";
import type { AppointmentDetails } from "./types";

type Props = { appointment: AppointmentDetails; onDone: (message: string) => void; onStale: () => void; onCancel: () => void };

export function ReschedulePanel({ appointment, onDone, onStale, onCancel }: Props) {
  const [startLocal, setStartLocal] = useState(utcIsoToTehranLocal(appointment.scheduled_start_at_utc));
  const [minutes, setMinutes] = useState(
    durationMinutes(appointment.scheduled_start_at_utc, appointment.scheduled_end_at_utc),
  );
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);
  const [conflicts, setConflicts] = useState<OverlapConflict[] | null>(null);
  const idem = useIdempotencyKey();
  const unchanged = startLocal === utcIsoToTehranLocal(appointment.scheduled_start_at_utc)
    && minutes === durationMinutes(appointment.scheduled_start_at_utc, appointment.scheduled_end_at_utc);
  const canSubmit = !busy && !!startLocal && minutes >= 1 && !unchanged;

  async function submit(acknowledge: boolean) {
    if (busy || !startLocal || minutes < 1) return;
    setBusy(true);
    setFailure(null);
    const start = tehranLocalToUtcIso(startLocal);
    const body = {
      start_at_utc: start,
      end_at_utc: addMinutesIso(start, minutes),
      acknowledge_overlap: acknowledge,
      acknowledged_conflict_ids: acknowledge && conflicts ? sortedConflictIds(conflicts) : [],
    };
    const result = await apiJson(`/api/v1/appointments/${appointment.appointment_id}/reschedule`, {
      method: "POST",
      version: appointment.aggregate_version,
      idempotencyKey: idem.keyFor({ id: appointment.appointment_id, v: appointment.aggregate_version, body }),
      body,
      fallbackMessage: "جابه‌جایی نوبت ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      const needed = extractOverlapConflicts(result.body);
      if (needed && !acknowledge) {
        setConflicts(needed);
        return;
      }
      setConflicts(null);
      setFailure(result);
      return;
    }
    idem.reset();
    setConflicts(null);
    onDone(result.replayed ? "درخواست جابه‌جایی قبلاً ثبت شده بود" : "نوبت جابه‌جا شد");
  }

  return (
    <section className="space-y-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-4" data-testid="reschedule-panel" aria-label="جابه‌جایی نوبت">
      <h3 className="ds-section-title">جابه‌جایی نوبت</h3>
      <p className="text-sm text-[var(--ds-text-muted)] tabular-nums">زمان فعلی: {formatTehran(appointment.scheduled_start_at_utc)}</p>
      <div className="grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <JalaliDateTimeField label="شروع جدید" testId="reschedule-start" value={startLocal} onChange={setStartLocal} />
        <TextField type="number" inputMode="numeric" min={1} max={1440} label="مدت (دقیقه)" value={minutes} onChange={(e) => setMinutes(Math.max(0, Math.floor(Number(e.target.value) || 0)))} data-testid="reschedule-minutes" />
      </div>
      {failure ? (
        <div className="space-y-2" data-testid="reschedule-error">
          <Alert>{failureMessage(failure)}</Alert>
          {failure.status === 412 ? <Button variant="ghost" onClick={onStale}>بارگذاری مجدد جزئیات</Button> : null}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button loading={busy} disabled={!canSubmit} onClick={() => void submit(false)} data-testid="reschedule-submit">
          {busy ? "در حال جابه‌جایی…" : "ثبت زمان جدید"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>انصراف</Button>
      </div>
      {conflicts ? (
        <OverlapDialog
          conflicts={conflicts}
          submitting={busy}
          confirmLabel="تأیید تداخل و جابه‌جایی"
          onConfirm={() => void submit(true)}
          onDismiss={() => setConflicts(null)}
        />
      ) : null}
    </section>
  );
}
