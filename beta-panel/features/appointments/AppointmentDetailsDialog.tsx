"use client";

import Link from "next/link";
import { useState } from "react";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { useSession } from "@/components/session/SessionProvider";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTehran } from "@/lib/client";
import { appointmentStatusLabel } from "@/lib/format/status";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { CancelPanel } from "./CancelPanel";
import { ReschedulePanel } from "./ReschedulePanel";
import type { AppointmentDetails } from "./types";

type Props = { appointmentId: string; onClose: () => void; onChanged: () => void };
type Mode = "view" | "cancel" | "reschedule";

const RESOURCE_TYPE_LABEL: Record<string, string> = { PRACTITIONER: "ارائه‌دهنده", ROOM: "اتاق", DEVICE: "دستگاه" };

export function AppointmentDetailsDialog({ appointmentId, onClose, onChanged }: Props) {
  const { can } = useSession();
  const toast = useToast();
  const [mode, setMode] = useState<Mode>("view");
  const query = useApiQuery<AppointmentDetails>(`/api/v1/appointments/${appointmentId}`, "بارگذاری جزئیات نوبت ناموفق بود");
  const detail = query.data;

  function done(message: string) {
    toast.success(message);
    onChanged();
    onClose();
  }

  return (
    <Dialog open size="lg" title="جزئیات نوبت" onClose={onClose} testId="appointment-dialog">
      <QueryBoundary loading={query.loading} error={query.error} deniedWhat="مشاهدهٔ جزئیات نوبت" onRetry={query.reload}>
        {detail && (
          <div className="space-y-4">
            <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2" data-testid="appointment-detail">
              <div><dt className="text-[var(--ds-text-muted)]">بیمار</dt><dd className="font-medium">
                {can(P.patientsViewProfile) ? (
                  <Link className="text-[var(--ds-primary)] hover:underline" href={`/patients/${detail.patient_profile_id}`} data-testid="appointment-patient-link">
                    {detail.patient_first_name} {detail.patient_last_name}
                  </Link>
                ) : `${detail.patient_first_name} ${detail.patient_last_name}`}
              </dd></div>
              <div><dt className="text-[var(--ds-text-muted)]">خدمت</dt><dd>{detail.service_name}</dd></div>
              <div><dt className="text-[var(--ds-text-muted)]">شروع</dt><dd className="tabular-nums">{formatTehran(detail.scheduled_start_at_utc)}</dd></div>
              <div><dt className="text-[var(--ds-text-muted)]">پایان</dt><dd className="tabular-nums">{formatTehran(detail.scheduled_end_at_utc)}</dd></div>
              <div><dt className="text-[var(--ds-text-muted)]">وضعیت</dt><dd><StatusBadge testId="appointment-status">{appointmentStatusLabel(detail.status)}</StatusBadge></dd></div>
              <div><dt className="text-[var(--ds-text-muted)]">کانال / ظرفیت</dt><dd>{detail.booking_channel === "MANUAL" ? "دستی" : "آنلاین"} — {detail.capacity_pool === "MANUAL" ? "ظرفیت دستی" : "ظرفیت آنلاین"}</dd></div>
              <div><dt className="text-[var(--ds-text-muted)]">ثبت</dt><dd className="tabular-nums">{formatTehran(detail.created_at_utc)}</dd></div>
              <div><dt className="text-[var(--ds-text-muted)]">آخرین تغییر</dt><dd className="tabular-nums">{formatTehran(detail.updated_at_utc)}</dd></div>
            </dl>
            <section aria-label="منابع تخصیص‌یافته">
              <h4 className="mb-1 font-semibold">منابع</h4>
              <ul className="space-y-1 text-sm" data-testid="appointment-allocations">
                {detail.allocations.map((a) => (
                  <li key={a.resource_id}>{RESOURCE_TYPE_LABEL[a.resource_type] ?? a.resource_type}: {a.resource_name}</li>
                ))}
                {!detail.allocations.length && <li className="text-[var(--ds-text-muted)]">منبعی ثبت نشده است</li>}
              </ul>
            </section>

            {mode === "view" && (
              <div className="flex flex-wrap items-center gap-2">
                {detail.can_reschedule && <button type="button" className="ds-btn ds-btn-primary" onClick={() => setMode("reschedule")} data-testid="appointment-reschedule">جابه‌جایی</button>}
                {detail.can_cancel && <button type="button" className="ds-btn ds-btn-ghost ds-btn-danger" onClick={() => setMode("cancel")} data-testid="appointment-cancel">لغو نوبت</button>}
                {!detail.can_cancel && !detail.can_reschedule && (
                  <p className="text-sm text-[var(--ds-text-muted)]" data-testid="appointment-readonly">
                    فقط نوبت‌های دستی با وضعیت «تأییدشده» قابل لغو یا جابه‌جایی‌اند و نیاز به مجوز مربوط دارند.
                  </p>
                )}
              </div>
            )}
            {mode === "cancel" && <CancelPanel appointment={detail} onDone={done} onStale={() => { setMode("view"); query.reload(); }} />}
            {mode === "reschedule" && <ReschedulePanel appointment={detail} onDone={done} onStale={() => { setMode("view"); query.reload(); }} />}
          </div>
        )}
      </QueryBoundary>
    </Dialog>
  );
}
