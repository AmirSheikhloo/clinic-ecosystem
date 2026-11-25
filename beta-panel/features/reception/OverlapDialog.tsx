"use client";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { formatTehran, type OverlapConflict } from "@/lib/client";

type Props = {
  conflicts: OverlapConflict[];
  submitting: boolean;
  onConfirm: () => void;
  onDismiss: () => void;
  confirmLabel?: string;
};

export function OverlapDialog({
  conflicts,
  submitting,
  onConfirm,
  onDismiss,
  confirmLabel = "تأیید تداخل و ثبت نوبت",
}: Props) {
  return (
    <Dialog open title="تأیید صریح تداخل نوبت دستی" onClose={onDismiss} testId="overlap-dialog">
      <div className="space-y-3">
        <p className="text-sm text-[var(--ds-text)]">
          این نوبت با نوبت‌های موجود هم‌پوشانی دارد. فقط داده‌های مجاز سرور نمایش داده می‌شود.
          ادامه فقط با تأیید آگاهانه و مجوز ALLOW_MANUAL_OVERBOOKING ممکن است.
        </p>
        <ul className="space-y-2 text-sm">
          {conflicts.map((conflict) => (
            <li
              key={conflict.appointment_id}
              className="rounded-[var(--ds-radius-md)] border border-[var(--ds-warning)] bg-[color-mix(in_srgb,var(--ds-warning)_10%,var(--ds-surface))] px-3 py-2"
            >
              <div>شناسه نوبت: {conflict.appointment_id}</div>
              {conflict.display_safe_patient_name !== undefined && (
                <div>بیمار: {conflict.display_safe_patient_name || "—"}</div>
              )}
              {conflict.scheduled_start_at_utc && (
                <div className="tabular-nums">زمان: {formatTehran(conflict.scheduled_start_at_utc)}</div>
              )}
              {conflict.booking_channel && <div>کانال: {conflict.booking_channel}</div>}
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            data-testid="overlap-confirm"
            disabled={submitting}
            onClick={onConfirm}
            className="ds-btn ds-btn-primary"
          >
            {submitting ? "در حال تأیید…" : confirmLabel}
          </button>
          <Button variant="ghost" disabled={submitting} onClick={onDismiss}>
            انصراف
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
