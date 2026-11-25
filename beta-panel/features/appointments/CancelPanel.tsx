"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { Button } from "@/components/ui/Button";
import { apiJson, type ApiFail } from "@/lib/api";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import { failureMessage } from "./action-errors";
import type { AppointmentDetails } from "./types";

type Props = { appointment: AppointmentDetails; onDone: (message: string) => void; onStale: () => void };

export function CancelPanel({ appointment, onDone, onStale }: Props) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<ApiFail | null>(null);
  const idem = useIdempotencyKey();

  async function submit() {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    const body = { reason: reason.trim() || null };
    const result = await apiJson(`/api/v1/appointments/${appointment.appointment_id}/cancel`, {
      method: "POST",
      version: appointment.aggregate_version,
      idempotencyKey: idem.keyFor({ id: appointment.appointment_id, v: appointment.aggregate_version, body }),
      body,
      fallbackMessage: "لغو نوبت ناموفق بود",
    });
    setBusy(false);
    if (!result.ok) {
      setFailure(result);
      return;
    }
    idem.reset();
    onDone(result.replayed ? "درخواست لغو قبلاً ثبت شده بود" : "نوبت لغو شد");
  }

  return (
    <div className="space-y-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3" data-testid="cancel-panel">
      <h4 className="font-semibold">لغو نوبت</h4>
      <TextAreaField label="دلیل (اختیاری)" rows={2} maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="cancel-reason" />
      {failure && (
        <div className="space-y-2" data-testid="cancel-error">
          <Alert>{failureMessage(failure)}</Alert>
          {failure.status === 412 && <Button variant="ghost" onClick={onStale}>بارگذاری مجدد جزئیات</Button>}
        </div>
      )}
      <Button variant="ghost" className="ds-btn-danger" disabled={busy} onClick={() => void submit()} data-testid="cancel-confirm">
        {busy ? "در حال لغو…" : "تأیید لغو نوبت"}
      </Button>
    </div>
  );
}
