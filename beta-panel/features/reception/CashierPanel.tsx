"use client";

import { useRef, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson } from "@/lib/api";
import { allocateFixedDiscountIrr, CheckoutIntentStore } from "@/lib/checkout-intent";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useSession } from "@/components/session/SessionProvider";
import { PrintActions } from "@/features/print/PrintActions";
import { tehranTodayJalaliLabel } from "@/lib/tehran";
import type { DraftServiceLine, Patient } from "./types";
import type { BookedSummary } from "./useDeskBookingState";

type Props = {
  patient: Patient | null;
  lines: DraftServiceLine[];
  draft?: DraftServiceLine | null;
  onRemove?: (key: string) => void;
  lastBooking?: BookedSummary | null;
  onCleared?: () => void;
};

type CheckoutResult = {
  id: string;
  invoice_number: string | null;
  status: string;
  receipt_id: string | null;
  patient_payable_total: number;
  allocated_total: number;
  outstanding: number;
  financial_status: string;
  received_irr?: number;
  applied_irr?: number;
  unapplied_credit_irr?: number;
};

function appointmentIdForLine(
  line: DraftServiceLine,
  lastBooking: BookedSummary | null | undefined,
): string | null {
  if (!lastBooking) return null;
  const fromLines = lastBooking.lines?.find(
    (item) => item.serviceId === line.serviceId || item.clientLineId === line.key,
  );
  if (fromLines) return fromLines.appointmentId;
  if (lastBooking.lines?.length === 1) return lastBooking.lines[0].appointmentId;
  if (!lastBooking.lines?.length) return lastBooking.appointmentId;
  return null;
}

/** Live reception cashier: durable intent key + server-tariff checkout. */
export function CashierPanel({ patient, lines, draft, onRemove, lastBooking, onCleared }: Props) {
  const { can } = useSession();
  const intentStore = useRef(new CheckoutIntentStore());
  const all = draft ? [...lines, draft] : lines;
  const previewTotal = all.reduce((sum, line) => sum + line.priceIrr, 0);
  const [discountFixed, setDiscountFixed] = useState(0);
  const [discountBps, setDiscountBps] = useState(0);
  const [payMethod, setPayMethod] = useState<"CASH" | "POS" | "NONE">("CASH");
  const [payAmount, setPayAmount] = useState<number | "">("");
  const [acceptCredit, setAcceptCredit] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CheckoutResult | null>(null);
  const [resultPatientDisplay, setResultPatientDisplay] = useState<string>("بیمار");
  const [resultLines, setResultLines] = useState<
    Array<{ description: string; amountIrr: number }>
  >([]);
  const [resultDiscountIrr, setResultDiscountIrr] = useState(0);
  const [resultPayMethod, setResultPayMethod] = useState<"CASH" | "POS" | "NONE">("NONE");

  const canPost = can(P.financeInvoiceDraft) && can(P.financeInvoicePost);
  const canPay = canPost && can(P.financeReceiptRecord);
  const canDiscount = can(P.financeDiscount);

  const fixedCuts =
    canDiscount && discountFixed > 0
      ? allocateFixedDiscountIrr(
          all.map((line) => line.priceIrr),
          discountFixed,
        )
      : all.map(() => 0);
  const bpsCut = canDiscount && discountBps > 0 ? Math.floor((previewTotal * discountBps) / 10_000) : 0;
  // Preview matches submission: either fixed OR percent (not both) — server rejects combine.
  const usingFixed = discountFixed > 0;
  const usingBps = !usingFixed && discountBps > 0;
  const payablePreview = Math.max(
    0,
    previewTotal - (usingFixed ? fixedCuts.reduce((s, v) => s + v, 0) : bpsCut),
  );

  async function checkout(mode: "post_only" | "pay") {
    if (!patient || lines.length === 0 || busy) return;
    if (mode === "pay" && !canPay) return;
    if (mode === "post_only" && !canPost) return;
    if (discountFixed > 0 && discountBps > 0) {
      setError("نمی‌توان تخفیف ثابت و درصدی را هم‌زمان اعمال کرد");
      return;
    }
    setBusy(true);
    setError(null);

    const submittedLines = lines.map((line, idx) => ({
      service_id: line.serviceId,
      appointment_id: appointmentIdForLine(line, lastBooking),
      description: line.serviceName,
      discount_amount: usingFixed && canDiscount ? fixedCuts[idx] ?? 0 : 0,
      discount_percent_bps: usingBps && canDiscount ? discountBps : null,
      charge_without_service_reason:
        appointmentIdForLine(line, lastBooking) == null ? "desk_manual_charge_authorized" : null,
    }));

    const paymentAmount =
      mode === "pay" && payMethod !== "NONE"
        ? Number(payAmount === "" ? payablePreview : payAmount)
        : null;

    const body = {
      patient_id: patient.patient_profile_id,
      post: true,
      accept_unapplied_credit: acceptCredit,
      payment_method: mode === "pay" && payMethod !== "NONE" ? payMethod : null,
      payment_amount_irr: paymentAmount,
      lines: submittedLines,
    };

    const intentKey = intentStore.current.keyFor({
      patientId: patient.patient_profile_id,
      lineServiceIds: lines.map((l) => l.serviceId),
      lineAppointmentIds: submittedLines.map((l) => l.appointment_id),
      discountFixed: usingFixed ? discountFixed : 0,
      discountBps: usingBps ? discountBps : 0,
      payMethod: mode === "pay" ? payMethod : "NONE",
      paymentAmountIrr: paymentAmount,
      acceptCredit,
      post: true,
    });

    const response = await apiJson<CheckoutResult>("/api/v1/finance/desk-checkout", {
      method: "POST",
      body,
      idempotencyKey: intentKey,
      fallbackMessage: "ثبت صورتحساب ناموفق بود",
    });
    setBusy(false);
    if (!response.ok) {
      setError(response.message);
      return;
    }
    intentStore.current.complete();
    setResult(response.data);
    setResultPatientDisplay(
      patient ? `${patient.first_name} ${patient.last_name}` : "بیمار",
    );
    setResultLines(
      lines.map((line) => ({ description: line.serviceName, amountIrr: line.priceIrr })),
    );
    setResultDiscountIrr(
      usingFixed ? fixedCuts.reduce((s, v) => s + v, 0) : usingBps ? bpsCut : 0,
    );
    setResultPayMethod(mode === "pay" && payMethod !== "NONE" ? payMethod : "NONE");
    onCleared?.();
  }

  return (
    <section className="ds-card space-y-3 p-5" aria-label="صندوق پذیرش" data-testid="cashier-panel">
      <div>
        <h2 className="ds-section-title">صندوق و صورتحساب</h2>
        <p className="ds-hint">
          پیش‌نویس زنده به صورتحساب رسمی، تخفیف، پرداخت نقدی/POS شبیه‌سازی‌شده و مانده تبدیل می‌شود. پرداخت زنده و بیمه فعال نیست.
        </p>
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
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium truncate">{line.serviceName}</p>
                  <p className="text-xs text-[var(--ds-text-muted)] tabular-nums">
                    {line.localStart || "زمان؟"} · {line.durationMinutes} دقیقه
                  </p>
                </div>
                <div className="shrink-0 text-end">
                  <p className="tabular-nums font-medium">{formatCount(line.priceIrr)}</p>
                  {onRemove && !line.key.startsWith("draft-") ? (
                    <button
                      type="button"
                      className="text-xs text-[var(--ds-danger)]"
                      onClick={() => onRemove(line.key)}
                      data-testid="invoice-remove-line"
                    >
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
        <span>جمع ناخالص</span>
        <span className="tabular-nums" data-testid="invoice-total">
          {formatCount(previewTotal)} ریال
        </span>
      </div>

      {canDiscount ? (
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="block text-sm">
            تخفیف ثابت (ریال)
            <input
              type="number"
              min={0}
              className="ds-input mt-1"
              value={discountFixed}
              onChange={(e) => {
                setDiscountFixed(Math.max(0, Number(e.target.value) || 0));
                if (Number(e.target.value) > 0) setDiscountBps(0);
              }}
              data-testid="cashier-discount"
            />
          </label>
          <label className="block text-sm">
            تخفیف درصدی (bps، 10000=100%)
            <input
              type="number"
              min={0}
              max={10000}
              className="ds-input mt-1"
              value={discountBps}
              onChange={(e) => {
                const next = Math.max(0, Math.min(10000, Number(e.target.value) || 0));
                setDiscountBps(next);
                if (next > 0) setDiscountFixed(0);
              }}
              data-testid="cashier-discount-bps"
            />
          </label>
        </div>
      ) : null}

      <div className="flex items-center justify-between text-sm">
        <span>قابل پرداخت پس از تخفیف</span>
        <span className="tabular-nums font-semibold" data-testid="cashier-payable">
          {formatCount(payablePreview)} ریال
        </span>
      </div>

      {canPost ? (
        <div className="space-y-2 border-t border-[var(--ds-border)] pt-3">
          {canPay ? (
            <div className="flex flex-wrap gap-2" role="group" aria-label="روش پرداخت">
              {(["CASH", "POS", "NONE"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`ds-btn ds-btn-sm ${payMethod === m ? "ds-btn-primary" : "ds-btn-ghost"}`}
                  onClick={() => setPayMethod(m)}
                  data-testid={`cashier-pay-${m.toLowerCase()}`}
                >
                  {m === "CASH" ? "نقد" : m === "POS" ? "کارتخوان" : "بدون دریافت"}
                </button>
              ))}
            </div>
          ) : (
            <p className="ds-hint">مجوز ثبت رسید ندارید — فقط ثبت صورتحساب بدون پرداخت ممکن است.</p>
          )}
          {canPay && payMethod !== "NONE" ? (
            <>
              <label className="block text-sm">
                مبلغ دریافتی (ریال)
                <input
                  type="number"
                  min={0}
                  className="ds-input mt-1"
                  value={payAmount}
                  placeholder={String(payablePreview)}
                  onChange={(e) =>
                    setPayAmount(e.target.value === "" ? "" : Math.max(0, Number(e.target.value) || 0))
                  }
                  data-testid="cashier-pay-amount"
                />
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={acceptCredit}
                  onChange={(e) => setAcceptCredit(e.target.checked)}
                  data-testid="cashier-accept-credit"
                />
                پذیرش اضافه پرداخت به‌عنوان اعتبار بیمار
              </label>
            </>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="primary"
              disabled={busy || lines.length === 0 || !patient}
              onClick={() => void checkout(canPay && payMethod !== "NONE" ? "pay" : "post_only")}
              data-testid="cashier-checkout"
            >
              {canPay && payMethod !== "NONE" ? "ثبت و دریافت" : "ثبت بدون دریافت"}
            </Button>
            {canPay && payMethod !== "NONE" ? (
              <Button
                type="button"
                variant="ghost"
                disabled={busy || lines.length === 0 || !patient}
                onClick={() => void checkout("post_only")}
                data-testid="cashier-post-only"
              >
                فقط ثبت صورتحساب
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      {error ? <Alert testId="cashier-error">{error}</Alert> : null}
      {result ? (
        <div className="space-y-3" data-testid="cashier-result">
          <div className="rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="ok">ثبت شد</StatusBadge>
              <span className="tabular-nums">شماره: {result.invoice_number ?? result.id}</span>
            </div>
            <p className="mt-1 text-[var(--ds-text-muted)]">
              وضعیت مالی: {result.financial_status} · مانده: {formatCount(result.outstanding)} ریال
            </p>
          </div>
          {can(P.financeInvoiceView) ? (
            <PrintActions
              invoices={[
                {
                  invoiceId: result.id,
                  invoiceNumber: result.invoice_number ?? result.id,
                  patientDisplay: resultPatientDisplay,
                  jalaliDate: tehranTodayJalaliLabel(),
                  lines: resultLines,
                  discountIrr: resultDiscountIrr || undefined,
                  totalPayableIrr: result.patient_payable_total,
                  paidIrr: result.received_irr ?? result.allocated_total,
                  methodLabel:
                    resultPayMethod === "CASH"
                      ? "نقدی"
                      : resultPayMethod === "POS"
                        ? "کارتخوان"
                        : "بدون دریافت",
                  financialStatus: result.financial_status,
                },
              ]}
            />
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
