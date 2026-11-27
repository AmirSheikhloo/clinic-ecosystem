"use client";

import { useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useSession } from "@/components/session/SessionProvider";
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
};

/** Live reception cashier: draft → discount → post → CASH/POS (synthetic). */
export function CashierPanel({ patient, lines, draft, onRemove, lastBooking, onCleared }: Props) {
  const { can } = useSession();
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

  const canCheckout = can(P.financeInvoiceDraft) && can(P.financeInvoicePost) && can(P.financeReceiptRecord);
  const bpsCut = discountBps > 0 ? Math.floor((previewTotal * discountBps) / 10_000) : 0;
  const payablePreview = Math.max(0, previewTotal - (discountFixed || 0) - bpsCut);

  async function checkout(mode: "post_only" | "pay") {
    if (!patient || lines.length === 0 || busy) return;
    setBusy(true);
    setError(null);
    const lineDiscountEach =
      discountFixed > 0 && can(P.financeDiscount)
        ? Math.floor(discountFixed / lines.length)
        : 0;
    const rem = discountFixed > 0 ? discountFixed - lineDiscountEach * lines.length : 0;
    const body = {
      patient_id: patient.patient_profile_id,
      post: true,
      accept_unapplied_credit: acceptCredit,
      payment_method: mode === "pay" && payMethod !== "NONE" ? payMethod : null,
      payment_amount_irr:
        mode === "pay" && payMethod !== "NONE"
          ? Number(payAmount === "" ? payablePreview : payAmount)
          : null,
      lines: lines.map((line, idx) => ({
        service_id: line.serviceId,
        appointment_id:
          lastBooking && lines.length === 1 ? lastBooking.appointmentId : null,
        description: line.serviceName,
        // Server tariff is authoritative; omit client price to avoid mismatch races.
        discount_amount: can(P.financeDiscount) ? lineDiscountEach + (idx === 0 ? rem : 0) : 0,
        discount_percent_bps: can(P.financeDiscount) && discountBps > 0 ? discountBps : null,
      })),
    };
    const stableKey = [
      "desk-checkout",
      patient.patient_profile_id,
      ...lines.map((l) => l.serviceId),
      String(discountFixed),
      String(discountBps),
      payMethod,
      String(body.payment_amount_irr ?? "none"),
    ].join(":");
    const response = await apiJson<CheckoutResult>("/api/v1/finance/desk-checkout", {
      method: "POST",
      body,
      idempotencyKey: stableKey.slice(0, 128),
      fallbackMessage: "ثبت صورتحساب ناموفق بود",
    });
    setBusy(false);
    if (!response.ok) {
      setError(response.message);
      return;
    }
    setResult(response.data);
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

      {can(P.financeDiscount) ? (
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="block text-sm">
            تخفیف ثابت (ریال)
            <input
              type="number"
              min={0}
              className="ds-input mt-1"
              value={discountFixed}
              onChange={(e) => setDiscountFixed(Math.max(0, Number(e.target.value) || 0))}
              data-testid="cashier-discount"
            />
          </label>
          <label className="block text-sm">
            تخفیف درصدی (bps، ۱۰۰۰۰=۱۰۰٪)
            <input
              type="number"
              min={0}
              max={10000}
              className="ds-input mt-1"
              value={discountBps}
              onChange={(e) => setDiscountBps(Math.max(0, Math.min(10000, Number(e.target.value) || 0)))}
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

      {canCheckout ? (
        <div className="space-y-2 border-t border-[var(--ds-border)] pt-3">
          <div className="flex flex-wrap gap-2" role="group" aria-label="روش پرداخت">
            {(["CASH", "POS", "NONE"] as const).map((m) => (
              <button
                key={m}
                type="button"
                className={`ds-btn ds-btn-ghost ${payMethod === m ? "!border-[var(--ds-primary)]" : ""}`}
                onClick={() => setPayMethod(m)}
                data-testid={`cashier-method-${m.toLowerCase()}`}
              >
                {m === "CASH" ? "نقدی" : m === "POS" ? "کارتخوان شبیه‌سازی" : "فقط ثبت"}
              </button>
            ))}
          </div>
          {payMethod !== "NONE" ? (
            <>
              <label className="block text-sm">
                مبلغ پرداخت (خالی = کامل)
                <input
                  type="number"
                  min={0}
                  className="ds-input mt-1"
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value === "" ? "" : Number(e.target.value))}
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
              loading={busy}
              disabled={!patient || lines.length === 0}
              onClick={() => void checkout(payMethod === "NONE" ? "post_only" : "pay")}
              data-testid="cashier-checkout"
            >
              {payMethod === "NONE" ? "ثبت صورتحساب" : "ثبت و دریافت"}
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-[var(--ds-text-muted)]">برای صندوق به مجوزهای مالی نیاز است.</p>
      )}

      {error ? <Alert tone="danger" testId="cashier-error">{error}</Alert> : null}
      {result ? (
        <div className="rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3 text-sm" data-testid="cashier-result">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={result.outstanding === 0 ? "ok" : result.allocated_total > 0 ? "warn" : "danger"}>
              {result.financial_status}
            </StatusBadge>
            <span className="tabular-nums">{result.invoice_number ?? result.id.slice(0, 8)}</span>
          </div>
          <p className="mt-2 tabular-nums">
            قابل پرداخت {formatCount(result.patient_payable_total)} · پرداخت‌شده {formatCount(result.allocated_total)} · مانده{" "}
            {formatCount(result.outstanding)}
          </p>
        </div>
      ) : null}
    </section>
  );
}
