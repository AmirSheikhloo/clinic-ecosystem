"use client";

import { formatCount } from "@/lib/format/numbers";
import type { DraftServiceLine, Patient } from "./types";

type Props = {
  patient: Patient | null;
  lines: DraftServiceLine[];
  draft?: DraftServiceLine | null;
  onRemove?: (key: string) => void;
};

/** Non-posted reception preview — tariffs from catalog; server remains authoritative. */
export function InvoicePreview({ patient, lines, draft, onRemove }: Props) {
  const all = draft ? [...lines, draft] : lines;
  const total = all.reduce((sum, line) => sum + line.priceIrr, 0);
  return (
    <section className="ds-card space-y-3 p-5" aria-label="پیش‌نمایش صورتحساب" data-testid="invoice-preview">
      <div>
        <h2 className="ds-section-title">پیش‌نمایش صورتحساب</h2>
        <p className="ds-hint">پیش‌نویس غیرثبت‌شده؛ قیمت نهایی پس از ثبت توسط سرور تأیید می‌شود. واحد: ریال.</p>
      </div>
      <p className="text-sm" data-testid="invoice-patient">
        بیمار:{" "}
        <span className="font-medium">
          {patient ? `${patient.first_name} ${patient.last_name}` : "—"}
        </span>
      </p>
      {all.length === 0 ? (
        <p className="ds-hint">هنوز خدمتی به پیش‌فاکتور اضافه نشده است.</p>
      ) : (
        <ul className="space-y-2" data-testid="invoice-lines">
          {all.map((line) => (
            <li
              key={line.key}
              className="rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2 text-sm"
              data-testid="invoice-line"
              data-draft={line.key.startsWith("draft-") ? "1" : "0"}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium truncate">{line.serviceName}</p>
                  <p className="text-xs text-[var(--ds-text-muted)] tabular-nums">
                    {line.localStart || "زمان؟"} · {line.durationMinutes} دقیقه
                    {line.resourceNames.length ? ` · ${line.resourceNames.join("، ")}` : ""}
                  </p>
                </div>
                <div className="shrink-0 text-end">
                  <p className="tabular-nums font-medium">{formatCount(line.priceIrr)}</p>
                  {onRemove && !line.key.startsWith("draft-") ? (
                    <button type="button" className="text-xs text-[var(--ds-danger)]" onClick={() => onRemove(line.key)} data-testid="invoice-remove-line">
                      حذف
                    </button>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-center justify-between border-t border-[var(--ds-border)] pt-3 text-sm font-semibold">
        <span>جمع قابل پرداخت (پیش‌نویس)</span>
        <span className="tabular-nums" data-testid="invoice-total">{formatCount(total)} ریال</span>
      </div>
      <p className="text-xs text-[var(--ds-text-muted)]">
        تخفیف، پرداخت و موجودی انبار در این نسخه فقط در صورت قرارداد Section 50 فعال می‌شوند.
      </p>
    </section>
  );
}
