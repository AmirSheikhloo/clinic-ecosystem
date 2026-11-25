"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { useToast } from "@/components/feedback/Toast";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTehran } from "@/lib/client";
import { appointmentStatusLabel, appointmentStatusTone, bookingChannelLabel, capacityPoolLabel } from "@/lib/format/status";
import { P } from "@/lib/permissions";
import { resourceTypeLabel } from "@/lib/resources";
import { useApiQuery } from "@/lib/use-api-query";
import { CancelPanel } from "./CancelPanel";
import { ReschedulePanel } from "./ReschedulePanel";
import type { AppointmentDetails } from "./types";

type Props = { appointmentId: string; onClose: () => void; onChanged: () => void };
type Mode = "view" | "cancel" | "reschedule";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-[var(--ds-text-muted)]">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

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

  function backToView(reload: boolean) {
    setMode("view");
    if (reload) query.reload();
  }

  return (
    <Dialog open placement="drawer" size="lg" title="جزئیات نوبت" onClose={onClose} testId="appointment-dialog">
      <QueryBoundary loading={query.loading} error={query.error} deniedWhat="مشاهدهٔ جزئیات نوبت" onRetry={query.reload}>
        {detail ? (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-lg font-semibold text-[var(--ds-heading)]">
                {can(P.patientsViewProfile) ? (
                  <Link className="hover:underline" href={`/patients/${detail.patient_profile_id}`} data-testid="appointment-patient-link">
                    {detail.patient_first_name} {detail.patient_last_name}
                  </Link>
                ) : (
                  `${detail.patient_first_name} ${detail.patient_last_name}`
                )}
              </p>
              <StatusBadge tone={appointmentStatusTone(detail.status)} testId="appointment-status">
                {appointmentStatusLabel(detail.status)}
              </StatusBadge>
            </div>
            <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2" data-testid="appointment-detail">
              <Row label="خدمت">{detail.service_name}</Row>
              <Row label="نوع ثبت">{bookingChannelLabel(detail.booking_channel)} — {capacityPoolLabel(detail.capacity_pool)}</Row>
              <Row label="شروع"><span className="tabular-nums">{formatTehran(detail.scheduled_start_at_utc)}</span></Row>
              <Row label="پایان"><span className="tabular-nums">{formatTehran(detail.scheduled_end_at_utc)}</span></Row>
              <Row label="زمان ثبت"><span className="tabular-nums">{formatTehran(detail.created_at_utc)}</span></Row>
              <Row label="آخرین تغییر"><span className="tabular-nums">{formatTehran(detail.updated_at_utc)}</span></Row>
            </dl>
            <section aria-label="منابع تخصیص‌یافته">
              <h3 className="ds-section-title mb-2">منابع</h3>
              <ul className="space-y-1 text-sm" data-testid="appointment-allocations">
                {detail.allocations.map((a) => (
                  <li key={a.resource_id} className="flex items-center gap-2">
                    <StatusBadge>{resourceTypeLabel(a.resource_type)}</StatusBadge>
                    {a.resource_name}
                  </li>
                ))}
                {!detail.allocations.length ? <li className="text-[var(--ds-text-muted)]">منبعی ثبت نشده است</li> : null}
              </ul>
            </section>

            {mode === "view" ? (
              <section className="space-y-3 border-t border-[var(--ds-border)] pt-4" aria-label="عملیات نوبت">
                <h3 className="ds-section-title">عملیات</h3>
                <div className="flex flex-wrap items-center gap-2">
                  {detail.can_reschedule ? <Button icon="calendar" onClick={() => setMode("reschedule")} data-testid="appointment-reschedule">جابه‌جایی</Button> : null}
                  {detail.can_cancel ? <Button variant="danger" icon="close" onClick={() => setMode("cancel")} data-testid="appointment-cancel">لغو نوبت</Button> : null}
                </div>
                {!detail.can_cancel && !detail.can_reschedule ? (
                  <p className="text-sm text-[var(--ds-text-muted)]" data-testid="appointment-readonly">
                    فقط نوبت‌های دستیِ «تأییدشده» قابل لغو یا جابه‌جایی‌اند و نیاز به مجوز مربوط دارند.
                  </p>
                ) : null}
                <p className="ds-hint">ثبت حضور، تکمیل و عدم حضور هنوز در این نسخه پشتیبانی نمی‌شود.</p>
              </section>
            ) : null}
            {mode === "cancel" ? <CancelPanel appointment={detail} onDone={done} onStale={() => backToView(true)} onBack={() => backToView(false)} /> : null}
            {mode === "reschedule" ? <ReschedulePanel appointment={detail} onDone={done} onStale={() => backToView(true)} onCancel={() => backToView(false)} /> : null}
          </div>
        ) : null}
      </QueryBoundary>
    </Dialog>
  );
}
