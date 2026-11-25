"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { Button } from "@/components/ui/Button";
import { apiJson, type ApiFail } from "@/lib/api";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import { failureMessage } from "./action-errors";
import type { AppointmentDetails } from "./types";

type Props = { appointment: AppointmentDetails; onDone: (message: string) => void; onStale: () => void; onBack: () => void };

export function CancelPanel({ appointment, onDone, onStale, onBack }: Props) {
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
    <section className="space-y-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-danger)] p-4" data-testid="cancel-panel" aria-label="لغو نوبت">
      <h3 className="ds-section-title">لغو نوبت</h3>
      <p className="text-sm text-[var(--ds-text-muted)]">با لغو، منابع تخصیص‌یافته آزاد می‌شود و این کار قابل بازگشت نیست.</p>
      <TextAreaField label="دلیل (اختیاری)" rows={2} maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="cancel-reason" />
      {failure ? (
        <div className="space-y-2" data-testid="cancel-error">
          <Alert>{failureMessage(failure)}</Alert>
          {failure.status === 412 ? <Button variant="ghost" onClick={onStale}>بارگذاری مجدد جزئیات</Button> : null}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button variant="danger-solid" loading={busy} onClick={() => void submit()} data-testid="cancel-confirm">
          {busy ? "در حال لغو…" : "تأیید لغو نوبت"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onBack}>بازگشت</Button>
      </div>
    </section>
  );
}
