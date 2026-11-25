"use client";

import { formatTehran, type OverlapConflict } from "@/lib/client";

type Props = {
  conflicts: OverlapConflict[];
  submitting: boolean;
  onConfirm: () => void;
  onDismiss: () => void;
};

export function OverlapDialog({ conflicts, submitting, onConfirm, onDismiss }: Props) {
  return (
    <section
      className="motion-dialog space-y-3 rounded-[var(--ds-radius-lg)] border border-[var(--ds-warning)] bg-[color-mix(in_srgb,var(--ds-warning)_12%,var(--ds-surface))] p-5"
      role="dialog"
      aria-labelledby="overlap-title"
      data-testid="overlap-dialog"
    >
      <h2 id="overlap-title" className="font-semibold text-[var(--ds-warning)]">
        تأیید صریح تداخل نوبت دستی
      </h2>
      <p className="text-sm text-[var(--ds-text)]">
        این نوبت با نوبت‌های موجود هم‌پوشانی دارد. فقط داده‌های مجاز سرور نمایش داده می‌شود.
        ادامه فقط با تأیید آگاهانه و مجوز ALLOW_MANUAL_OVERBOOKING ممکن است.
      </p>
      <ul className="space-y-2 text-sm">
        {conflicts.map((conflict) => (
          <li
            key={conflict.appointment_id}
            className="rounded-[var(--ds-radius-md)] bg-[var(--ds-surface)] px-3 py-2"
          >
            <div>شناسه نوبت: {conflict.appointment_id}</div>
            {conflict.display_safe_patient_name !== undefined && (
              <div>بیمار: {conflict.display_safe_patient_name || "—"}</div>
            )}
            {conflict.scheduled_start_at_utc && (
              <div className="tabular-nums">
                زمان: {formatTehran(conflict.scheduled_start_at_utc)}
              </div>
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
          {submitting ? "در حال تأیید…" : "تأیید تداخل و ثبت نوبت"}
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={onDismiss}
          className="ds-btn ds-btn-ghost"
        >
          انصراف
        </button>
      </div>
    </section>
  );
}
