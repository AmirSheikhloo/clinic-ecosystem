"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { formatTehran, tehranYmdOf } from "@/lib/client";
import type { BookedSummary } from "./useDeskBookingState";

type Props = { message: string; booking: BookedSummary; onNext: () => void };

/** Success summary shown after a booking; it keeps the form intact so a repeat submit replays safely. */
export function BookingConfirmation({ message, booking, onNext }: Props) {
  const trackingCode = message.match(/کد پیگیری: ([0-9a-f-]{36})/i)?.[1] ?? booking.appointmentId;
  return (
    <section className="ds-alert ds-alert-ok flex-col !items-stretch gap-3" role="status" data-testid="desk-status" aria-label="نتیجهٔ ثبت نوبت">
      <div className="flex items-start gap-2">
        <Icon name="success" className="mt-1" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">
            {booking.overlapAcknowledged ? "نوبت با تأیید تداخل ثبت شد" : "نوبت ثبت شد"}
            {booking.replayed ? " (بازیابی تکرار)" : ""}
          </p>
          <p className="text-sm tabular-nums">
            {booking.patientName}
            {booking.serviceName ? ` — ${booking.serviceName}` : ""} — {formatTehran(booking.startIso)}
          </p>
          <p className="text-xs opacity-80">
            کد پیگیری: <span className="tabular-nums" dir="ltr">{trackingCode}</span>
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button icon="user" onClick={onNext} data-testid="desk-next-patient">
          بیمار بعدی
        </Button>
        <Link href={`/appointments?date=${tehranYmdOf(booking.startIso)}`} className="ds-btn ds-btn-ghost" data-testid="desk-open-calendar">
          مشاهده در تقویم
        </Link>
        <Link href={`/patients/${booking.patientId}`} className="ds-btn ds-btn-ghost">
          پروندهٔ بیمار
        </Link>
      </div>
    </section>
  );
}
