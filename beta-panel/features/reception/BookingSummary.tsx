import { formatTehran } from "@/lib/client";
import { tehranLocalToUtcIso } from "@/lib/tehran";
import type { Patient, Service } from "./types";

type Props = {
  patient: Patient | null;
  service: Service | undefined;
  resourceNames: string[];
  localStart: string;
  endLabel: string | null;
  durationMinutes: number;
};

type Line = { label: string; value: string | null; testId: string };

/** Read-only review of what will be booked, shown before the submit button. */
export function BookingSummary({ patient, service, resourceNames, localStart, endLabel, durationMinutes }: Props) {
  const when = localStart ? safeFormat(localStart) : null;
  const lines: Line[] = [
    { label: "بیمار", value: patient ? `${patient.first_name} ${patient.last_name}` : null, testId: "summary-patient" },
    { label: "خدمت", value: service?.service_name ?? null, testId: "summary-service" },
    { label: "منابع", value: resourceNames.length ? resourceNames.join("، ") : null, testId: "summary-resources" },
    {
      label: "زمان",
      value: when ? `${when}${endLabel ? ` تا ${endLabel}` : ""}${service ? ` (${durationMinutes} دقیقه)` : ""}` : null,
      testId: "summary-time",
    },
  ];
  return (
    <section className="ds-summary" aria-label="مرور نوبت" data-testid="booking-summary">
      <h3 className="text-sm font-semibold text-[var(--ds-heading)]">مرور نوبت</h3>
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
        {lines.map((line) => (
          <div key={line.testId} className="contents">
            <dt className="text-[var(--ds-text-muted)]">{line.label}</dt>
            <dd className={`min-w-0 break-words tabular-nums ${line.value ? "" : "text-[var(--ds-text-muted)]"}`} data-testid={line.testId}>
              {line.value ?? "—"}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function safeFormat(localStart: string): string | null {
  try {
    return formatTehran(tehranLocalToUtcIso(localStart));
  } catch {
    return null;
  }
}
