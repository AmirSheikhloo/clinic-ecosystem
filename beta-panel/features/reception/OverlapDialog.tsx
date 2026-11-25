"use client";

import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { formatTehran, type OverlapConflict } from "@/lib/client";
import { bookingChannelLabel } from "@/lib/format/status";

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
    <Dialog
      open
      title="تداخل با نوبت‌های موجود"
      description="زمان یا منبع انتخاب‌شده با نوبت‌های زیر هم‌پوشانی دارد."
      onClose={onDismiss}
      testId="overlap-dialog"
      footer={
        <>
          <Button variant="ghost" disabled={submitting} onClick={onDismiss}>
            انصراف
          </Button>
          <Button loading={submitting} onClick={onConfirm} data-testid="overlap-confirm">
            {submitting ? "در حال تأیید…" : confirmLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Alert tone="warn">
          ادامه فقط با تأیید آگاهانه شما و داشتن مجوز «تأیید تداخل نوبت دستی» ممکن است. در غیر این صورت انصراف دهید و زمان یا منبع دیگری انتخاب کنید.
        </Alert>
        <ul className="space-y-2 text-sm">
          {conflicts.map((conflict) => (
            <li
              key={conflict.appointment_id}
              className="rounded-[var(--ds-radius-md)] border border-[var(--ds-warning)] bg-[color-mix(in_srgb,var(--ds-warning)_10%,var(--ds-surface))] px-3 py-2"
            >
              {conflict.display_safe_patient_name !== undefined ? (
                <div className="font-medium">بیمار: {conflict.display_safe_patient_name || "—"}</div>
              ) : null}
              {conflict.scheduled_start_at_utc ? (
                <div className="tabular-nums">زمان: {formatTehran(conflict.scheduled_start_at_utc)}</div>
              ) : null}
              {conflict.booking_channel ? <div>نوع ثبت: {bookingChannelLabel(conflict.booking_channel)}</div> : null}
              {conflict.display_safe_patient_name === undefined && !conflict.scheduled_start_at_utc ? <div>نوبت ثبت‌شدهٔ دیگر</div> : null}
            </li>
          ))}
        </ul>
      </div>
    </Dialog>
  );
}
