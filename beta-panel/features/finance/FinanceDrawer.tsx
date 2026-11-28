"use client";

import { useEffect, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiJson } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useSession } from "@/components/session/SessionProvider";
import {
  ADJUSTMENT_REASONS,
  DISCOUNT_REASONS,
  MONEY_OUT_APPROVAL_THRESHOLD_IRR,
  REFUND_REASONS,
  reasonRequiresExplanation,
} from "./finance-reasons";

export type FinanceDrawerTarget = {
  appointmentId: string;
  patientProfileId: string;
  patientName: string;
  serviceName: string;
  invoiceId?: string | null;
};

type InvoiceDetail = {
  id: string;
  invoice_number: string | null;
  status: string;
  financial_status: string;
  outstanding: number;
  patient_payable_total: number;
  allocated_total: number;
  lines: Array<{
    id: string;
    description: string;
    service_id: string | null;
    appointment_id: string | null;
    patient_payable_amount: number;
    line_status: string;
  }>;
  allocations?: Array<{
    id: string;
    payment_method: string;
    amount_irr: number;
    receipt_number?: string | null;
  }>;
};

type Props = {
  open: boolean;
  target: FinanceDrawerTarget | null;
  onClose: () => void;
};

/**
 * Shared left-side overlay finance drawer (dashboard + appointment management).
 * Append-only financial ops — never mutates verified historical receipt facts.
 */
export function FinanceDrawer({ open, target, onClose }: Props) {
  const { can } = useSession();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [reasonCode, setReasonCode] = useState("STAFF_COURTESY");
  const [reasonText, setReasonText] = useState("");
  const [discountValue, setDiscountValue] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || !target) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setInvoice(null);
    void (async () => {
      if (target.invoiceId) {
        const detail = await apiJson<InvoiceDetail>(`/api/v1/finance/invoices/${target.invoiceId}`, {
          fallbackMessage: "بارگذاری صورتحساب ناموفق بود",
        });
        if (cancelled) return;
        setLoading(false);
        if (!detail.ok) {
          setError(detail.message);
          return;
        }
        setInvoice(detail.data);
        return;
      }
      const list = await apiJson<{ items: Array<{ id: string }> }>(
        `/api/v1/finance/invoices?patient_id=${target.patientProfileId}&limit=10`,
        { fallbackMessage: "بارگذاری وضعیت مالی ناموفق بود" },
      );
      if (cancelled) return;
      if (!list.ok) {
        setLoading(false);
        setError(list.message);
        return;
      }
      const first = list.data.items[0];
      if (!first) {
        setLoading(false);
        setInvoice(null);
        return;
      }
      const detail = await apiJson<InvoiceDetail>(`/api/v1/finance/invoices/${first.id}`, {
        fallbackMessage: "بارگذاری صورتحساب ناموفق بود",
      });
      if (cancelled) return;
      setLoading(false);
      if (!detail.ok) {
        setError(detail.message);
        return;
      }
      setInvoice(detail.data);
    })();
    return () => {
      cancelled = true;
    };
  }, [open, target]);

  const needsExplain = reasonRequiresExplanation(DISCOUNT_REASONS, reasonCode);
  const moneyOutNeedsConfirm = (invoice?.outstanding ?? 0) >= MONEY_OUT_APPROVAL_THRESHOLD_IRR;

  async function applyDraftDiscount() {
    if (!invoice || !can(P.financeDiscount) || busy) return;
    if (needsExplain && !reasonText.trim()) {
      setError("برای «سایر» توضیح الزامی است");
      return;
    }
    setBusy(true);
    setError(null);
    const response = await apiJson(`/api/v1/finance/discounts`, {
      method: "POST",
      body: {
        invoice_id: invoice.id,
        discount_scope: "INVOICE",
        calculation_kind: "FIXED_IRR",
        requested_value: discountValue,
        reason_code: reasonCode,
        reason_text: reasonText.trim() || null,
      },
      fallbackMessage: "اعمال تخفیف ناموفق بود",
    });
    setBusy(false);
    if (!response.ok) {
      setError(response.message);
      return;
    }
    const refreshed = await apiJson<InvoiceDetail>(`/api/v1/finance/invoices/${invoice.id}`, {
      fallbackMessage: "نوسازی صورتحساب ناموفق بود",
    });
    if (refreshed.ok) setInvoice(refreshed.data);
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="وضعیت مالی نوبت"
      description={target ? `${target.patientName} · ${target.serviceName}` : undefined}
      placement="drawer"
      testId="finance-drawer"
    >
      {loading ? <Skeleton className="h-40" /> : null}
      {error ? (
        <Alert tone="danger" testId="finance-drawer-error">
          {error}
        </Alert>
      ) : null}
      {!loading && !invoice ? (
        <p className="ds-hint" data-testid="finance-drawer-empty">
          صورتحساب مرتبطی برای این نوبت یافت نشد.
        </p>
      ) : null}
      {invoice ? (
        <div className="space-y-4" data-testid="finance-drawer-invoice">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={invoice.status === "POSTED" ? "ok" : "neutral"}>
              {invoice.status}
            </StatusBadge>
            <span className="text-sm tabular-nums">
              {invoice.invoice_number ?? invoice.id.slice(0, 8)}
            </span>
            <span className="text-sm text-[var(--ds-text-muted)]">{invoice.financial_status}</span>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-[var(--ds-text-muted)]">قابل پرداخت</dt>
              <dd className="tabular-nums font-medium">
                {formatCount(invoice.patient_payable_total)} ریال
              </dd>
            </div>
            <div>
              <dt className="text-[var(--ds-text-muted)]">مانده</dt>
              <dd className="tabular-nums font-medium" data-testid="finance-drawer-outstanding">
                {formatCount(invoice.outstanding)} ریال
              </dd>
            </div>
          </dl>
          <section aria-label="ردیف‌های خدمت">
            <h3 className="text-sm font-semibold">ردیف‌های خدمت</h3>
            <ul className="mt-2 space-y-2">
              {(invoice.lines ?? []).map((ln) => (
                <li
                  key={ln.id}
                  className="rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2 text-sm"
                  data-testid="finance-drawer-line"
                  data-linked-appointment={
                    target && ln.appointment_id === target.appointmentId ? "1" : "0"
                  }
                >
                  <div className="flex justify-between gap-2">
                    <span className="truncate">{ln.description}</span>
                    <span className="tabular-nums shrink-0">
                      {formatCount(ln.patient_payable_amount)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
          <section aria-label="تاریخچه پرداخت">
            <h3 className="text-sm font-semibold">روش‌ها و تاریخچه پرداخت</h3>
            {(invoice.allocations ?? []).length === 0 ? (
              <p className="ds-hint mt-1">پرداختی ثبت نشده است.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-sm">
                {(invoice.allocations ?? []).map((a) => (
                  <li key={a.id} className="flex justify-between gap-2">
                    <span>
                      {a.payment_method}
                      {a.receipt_number ? ` · ${a.receipt_number}` : ""}
                    </span>
                    <span className="tabular-nums">{formatCount(a.amount_irr)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          {can(P.financeDiscount) && invoice.status === "DRAFT" ? (
            <section className="space-y-2 border-t border-[var(--ds-border)] pt-3" aria-label="تخفیف">
              <h3 className="text-sm font-semibold">تخفیف پیش‌نویس</h3>
              <label className="block text-sm">
                دلیل
                <select
                  className="ds-input mt-1"
                  value={reasonCode}
                  onChange={(e) => setReasonCode(e.target.value)}
                  data-testid="finance-drawer-discount-reason"
                >
                  {DISCOUNT_REASONS.map((r) => (
                    <option key={r.code} value={r.code}>
                      {r.labelFa}
                    </option>
                  ))}
                </select>
              </label>
              {needsExplain ? (
                <label className="block text-sm">
                  توضیح (الزامی)
                  <textarea
                    className="ds-input mt-1"
                    rows={2}
                    value={reasonText}
                    onChange={(e) => setReasonText(e.target.value)}
                    data-testid="finance-drawer-discount-explain"
                  />
                </label>
              ) : null}
              <label className="block text-sm">
                مبلغ تخفیف (ریال)
                <input
                  type="number"
                  min={0}
                  className="ds-input mt-1"
                  value={discountValue}
                  onChange={(e) => setDiscountValue(Math.max(0, Number(e.target.value) || 0))}
                  data-testid="finance-drawer-discount-value"
                />
              </label>
              <Button
                type="button"
                variant="subtle"
                disabled={busy}
                onClick={() => void applyDraftDiscount()}
                data-testid="finance-drawer-apply-discount"
              >
                اعمال تخفیف
              </Button>
            </section>
          ) : null}
          <p className="ds-hint text-xs">
            اصلاح و استرداد فقط از طریق عملیات الحاقی مجاز است
            {can(P.financeRefund) ? ` (${REFUND_REASONS.length} دلیل از پیش‌تعریف)` : ""}
            {can(P.financeAdjustment) ? ` · تعدیل: ${ADJUSTMENT_REASONS.length} دلیل` : ""}
            {moneyOutNeedsConfirm ? " · خروج وجه بزرگ نیازمند تأیید مدیر است" : ""}. حقایق مالی
            تأییدشدهٔ تاریخی تغییر نمی‌کنند.
          </p>
        </div>
      ) : null}
    </Dialog>
  );
}
