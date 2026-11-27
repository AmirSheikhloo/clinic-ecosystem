"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Alert } from "@/components/feedback/Alert";
import { QueryBoundary } from "@/components/feedback/QueryBoundary";
import { SelectField } from "@/components/forms/SelectField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { useSession } from "@/components/session/SessionProvider";
import { useToast } from "@/components/feedback/Toast";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery } from "@/lib/api";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import { useIdempotencyKey } from "@/lib/use-idempotency";
import {
  ADJUSTMENT_REASONS,
  DISCOUNT_REASONS,
  MONEY_OUT_APPROVAL_THRESHOLD_IRR,
  REFUND_REASONS,
  reasonRequiresExplanation,
} from "./finance-reasons";

export type FinanceDrawerTarget = {
  appointmentId: string;
  patientId: string;
  patientName: string;
  serviceName?: string;
};

type InvoiceRow = {
  id: string;
  invoice_number: string | null;
  status: string;
  patient_id: string;
  financial_status: string;
  patient_payable_total: number;
  allocated_total: number;
  outstanding: number;
};

type InvoiceDetail = {
  id: string;
  invoice_number: string | null;
  status: string;
  patient_id: string;
  financial_status: string;
  patient_payable_total: number;
  allocated_total: number;
  outstanding: number;
  lines: Array<{
    id: string;
    description: string;
    patient_payable_amount: number;
    discount_amount: number;
    appointment_id: string | null;
    service_id: string | null;
    line_kind?: string;
  }>;
  allocations: Array<{
    id: string;
    receipt_id: string;
    invoice_line_id: string;
    allocation_kind: string;
    amount_irr: number;
    payment_method: string;
    receipt_number?: string;
  }>;
};

type Balance = {
  outstanding_total?: number;
  patient_credit_irr?: number;
};

type Props = {
  target: FinanceDrawerTarget | null;
  onClose: () => void;
};

function tone(fs: string) {
  if (fs === "PAID") return "ok" as const;
  if (fs === "PARTIAL") return "warn" as const;
  return "danger" as const;
}

/**
 * Shared left-side overlay finance drawer (FIN-03).
 * Does not mutate historical verified financial facts — only appends discounts/
 * adjustments/refunds through authorized APIs.
 */
export function AppointmentFinanceDrawer({ target, onClose }: Props) {
  const { can, status } = useSession();
  const toast = useToast();
  const idem = useIdempotencyKey();
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [op, setOp] = useState<"discount" | "adjust" | "refund" | null>(null);
  const [reasonCode, setReasonCode] = useState("");
  const [reasonText, setReasonText] = useState("");
  const [amount, setAmount] = useState(0);
  const [approved, setApproved] = useState(false);

  const allowed = can(P.financeInvoiceView);
  const invoices = useApiQuery<{ items: InvoiceRow[] }>(
    status === "ready" && allowed && target
      ? `/api/v1/finance/invoices${buildQuery({ patient_id: target.patientId, limit: 40 })}`
      : null,
    "بارگذاری صورتحساب‌ها ناموفق بود",
    refresh,
  );
  const balance = useApiQuery<Balance>(
    status === "ready" && allowed && target
      ? `/api/v1/finance/patients/${target.patientId}/balance`
      : null,
    "بارگذاری مانده ناموفق بود",
    refresh,
  );

  const linked = useMemo(() => {
    const items = invoices.data?.items ?? [];
    return items;
  }, [invoices.data]);

  const preferredId = linked[0]?.id ?? null;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const invoiceId = selectedId ?? preferredId;

  const detail = useApiQuery<InvoiceDetail>(
    status === "ready" && allowed && invoiceId ? `/api/v1/finance/invoices/${invoiceId}` : null,
    "بارگذاری جزئیات صورتحساب ناموفق بود",
    refresh,
  );

  const appointmentLines =
    detail.data?.lines.filter(
      (ln) => !target?.appointmentId || ln.appointment_id === target.appointmentId || !ln.appointment_id,
    ) ?? [];
  const serviceLine =
    appointmentLines.find((ln) => ln.appointment_id === target?.appointmentId) ?? appointmentLines[0] ?? null;

  const applyAllocations =
    detail.data?.allocations.filter((a) => a.allocation_kind === "APPLY") ?? [];
  const refundEligible = applyAllocations.reduce((s, a) => s + a.amount_irr, 0);
  const outstanding = detail.data?.outstanding ?? linked[0]?.outstanding ?? 0;

  function resetOp() {
    setOp(null);
    setReasonCode("");
    setReasonText("");
    setAmount(0);
    setApproved(false);
    setError(null);
  }

  async function submitOp() {
    if (!detail.data || !op || busy) return;
    const catalog =
      op === "discount" ? DISCOUNT_REASONS : op === "adjust" ? ADJUSTMENT_REASONS : REFUND_REASONS;
    if (!reasonCode) {
      setError("انتخاب دلیل الزامی است");
      return;
    }
    if (reasonRequiresExplanation(catalog, reasonCode) && !reasonText.trim()) {
      setError("برای «سایر» توضیح الزامی است");
      return;
    }
    if (amount <= 0 && op !== "discount") {
      setError("مبلغ باید بزرگ‌تر از صفر باشد");
      return;
    }
    if (op !== "discount" && amount >= MONEY_OUT_APPROVAL_THRESHOLD_IRR && !approved) {
      setError(`مبالغ از ${formatCount(MONEY_OUT_APPROVAL_THRESHOLD_IRR)} ریال نیاز به تأیید صریح دارند`);
      return;
    }
    if (!serviceLine) {
      setError("ردیف خدمت مرتبط یافت نشد");
      return;
    }
    setBusy(true);
    setError(null);

    let result;
    if (op === "discount") {
      if (!can(P.financeDiscount) || detail.data.status !== "DRAFT") {
        setBusy(false);
        setError(detail.data.status !== "DRAFT" ? "تخفیف پیش‌نویس فقط روی DRAFT مجاز است" : "مجوز تخفیف ندارید");
        return;
      }
      result = await apiJson("/api/v1/finance/discounts", {
        method: "POST",
        body: {
          invoice_id: detail.data.id,
          invoice_line_id: serviceLine.id,
          discount_scope: "LINE",
          calculation_kind: "FIXED_AMOUNT",
          requested_value: amount,
          reason_code: reasonCode,
        },
        idempotencyKey: idem.keyFor({ op, id: detail.data.id, line: serviceLine.id, amount, reasonCode }),
        fallbackMessage: "ثبت تخفیف ناموفق بود",
      });
    } else if (op === "adjust") {
      if (!can(P.financeAdjustment)) {
        setBusy(false);
        setError("مجوز تعدیل ندارید");
        return;
      }
      if (detail.data.status === "DRAFT") {
        setBusy(false);
        setError("تعدیل روی پیش‌نویس مجاز نیست");
        return;
      }
      result = await apiJson("/api/v1/finance/adjustments", {
        method: "POST",
        body: {
          invoice_id: detail.data.id,
          invoice_line_id: serviceLine.id,
          adjustment_kind: amount < 0 ? "POST_PAYMENT_DISCOUNT" : "CORRECTION",
          patient_delta_irr: -Math.abs(amount),
          reason_code: reasonCode,
          reason_text: reasonText.trim() || catalog.find((r) => r.code === reasonCode)?.labelFa || "",
        },
        idempotencyKey: idem.keyFor({ op, id: detail.data.id, line: serviceLine.id, amount, reasonCode }),
        fallbackMessage: "ثبت تعدیل ناموفق بود",
      });
    } else {
      if (!can(P.financeRefund)) {
        setBusy(false);
        setError("مجوز استرداد ندارید");
        return;
      }
      const apply = applyAllocations[0];
      if (!apply) {
        setBusy(false);
        setError("تخصیص قابل استرداد وجود ندارد");
        return;
      }
      const refundAmount = Math.min(amount, apply.amount_irr);
      result = await apiJson("/api/v1/finance/refunds", {
        method: "POST",
        body: {
          original_receipt_id: apply.receipt_id,
          invoice_id: detail.data.id,
          invoice_line_id: apply.invoice_line_id,
          original_allocation_id: apply.id,
          amount_irr: refundAmount,
          refund_method: apply.payment_method === "POS" ? "POS" : "CASH",
          reason_code: reasonCode,
          idempotency_key: idem.keyFor({
            op,
            id: detail.data.id,
            alloc: apply.id,
            amount: refundAmount,
            reasonCode,
          }),
        },
        fallbackMessage: "ثبت استرداد ناموفق بود",
      });
    }

    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    idem.reset();
    toast.success(op === "discount" ? "تخفیف ثبت شد" : op === "adjust" ? "تعدیل ثبت شد" : "استرداد ثبت شد");
    resetOp();
    setRefresh((v) => v + 1);
  }

  const reasons =
    op === "discount" ? DISCOUNT_REASONS : op === "adjust" ? ADJUSTMENT_REASONS : op === "refund" ? REFUND_REASONS : [];

  return (
    <Dialog
      open={!!target}
      placement="drawer"
      size="lg"
      title="وضعیت مالی نوبت"
      description={target ? `${target.patientName}${target.serviceName ? ` — ${target.serviceName}` : ""}` : undefined}
      onClose={() => {
        resetOp();
        onClose();
      }}
      testId="appointment-finance-drawer"
    >
      {!allowed ? (
        <Alert tone="danger">مشاهدهٔ وضعیت مالی نیازمند مجوز FINANCE است.</Alert>
      ) : (
        <QueryBoundary loading={invoices.loading} error={invoices.error} deniedWhat="مشاهدهٔ مالی" onRetry={invoices.reload}>
          <div className="space-y-4" data-testid="finance-drawer-body">
            <dl className="grid gap-3 sm:grid-cols-2 text-sm">
              <div>
                <dt className="text-xs text-[var(--ds-text-muted)]">ماندهٔ بیمار</dt>
                <dd className="tabular-nums font-semibold" data-testid="finance-drawer-outstanding">
                  {formatCount(balance.data?.outstanding_total ?? outstanding)} ریال
                </dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--ds-text-muted)]">اعتبار بیمار</dt>
                <dd className="tabular-nums">{formatCount(balance.data?.patient_credit_irr ?? 0)} ریال</dd>
              </div>
            </dl>

            {linked.length === 0 ? (
              <p className="ds-hint" data-testid="finance-drawer-empty">
                صورتحسابی برای این بیمار یافت نشد.
              </p>
            ) : (
              <label className="block text-sm">
                صورتحساب مرتبط
                <select
                  className="ds-input mt-1"
                  value={invoiceId ?? ""}
                  onChange={(e) => setSelectedId(e.target.value || null)}
                  data-testid="finance-drawer-invoice-select"
                >
                  {linked.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {(inv.invoice_number ?? inv.id.slice(0, 8)) + ` — ${inv.financial_status}`}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {detail.data ? (
              <section className="space-y-3" aria-label="جزئیات صورتحساب">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={tone(detail.data.financial_status)} testId="finance-drawer-status">
                    {detail.data.financial_status}
                  </StatusBadge>
                  <span className="tabular-nums text-sm">{detail.data.invoice_number ?? detail.data.id.slice(0, 8)}</span>
                  <span className="text-xs text-[var(--ds-text-muted)]">{detail.data.status}</span>
                </div>

                <ul className="space-y-2" data-testid="finance-drawer-lines">
                  {(serviceLine ? [serviceLine] : detail.data.lines).map((ln) => (
                    <li
                      key={ln.id}
                      className="rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] px-3 py-2 text-sm"
                      data-testid="finance-drawer-line"
                    >
                      <div className="flex justify-between gap-2">
                        <span className="min-w-0 truncate font-medium">{ln.description}</span>
                        <span className="tabular-nums shrink-0">{formatCount(ln.patient_payable_amount)}</span>
                      </div>
                      {ln.appointment_id === target?.appointmentId ? (
                        <p className="text-xs text-[var(--ds-primary)]">مرتبط با این نوبت</p>
                      ) : null}
                    </li>
                  ))}
                </ul>

                <div>
                  <h4 className="ds-section-title mb-2">تاریخچهٔ پرداخت</h4>
                  {applyAllocations.length === 0 ? (
                    <p className="ds-hint">پرداخت ثبت‌شده‌ای نیست.</p>
                  ) : (
                    <ul className="space-y-1 text-sm" data-testid="finance-drawer-payments">
                      {applyAllocations.map((a) => (
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
                  <p className="mt-2 text-sm">
                    سقف استرداد واجد شرایط:{" "}
                    <span className="tabular-nums font-medium" data-testid="finance-drawer-refund-cap">
                      {formatCount(refundEligible)} ریال
                    </span>
                  </p>
                </div>

                <p className="text-xs text-[var(--ds-text-muted)]">
                  حقایق مالی تأییدشدهٔ تاریخی تغییر نمی‌کنند؛ فقط عملیات الحاقی مجاز است.
                </p>

                {!op ? (
                  <div className="flex flex-wrap gap-2 border-t border-[var(--ds-border)] pt-3">
                    {can(P.financeDiscount) && detail.data.status === "DRAFT" ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setOp("discount");
                          setAmount(0);
                        }}
                        data-testid="finance-drawer-discount"
                      >
                        تخفیف پیش‌نویس
                      </Button>
                    ) : null}
                    {can(P.financeAdjustment) && detail.data.status !== "DRAFT" ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setOp("adjust");
                          setAmount(10_000);
                        }}
                        data-testid="finance-drawer-adjust"
                      >
                        تخفیف/اصلاح پس از پرداخت
                      </Button>
                    ) : null}
                    {can(P.financeRefund) && refundEligible > 0 ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setOp("refund");
                          setAmount(Math.min(10_000, refundEligible));
                        }}
                        data-testid="finance-drawer-refund"
                      >
                        استرداد
                      </Button>
                    ) : null}
                    {can(P.patientsViewProfile) ? (
                      <Link
                        href={`/patients/${detail.data.patient_id}`}
                        className="ds-btn ds-btn-subtle ds-btn-sm"
                        data-testid="finance-drawer-patient-link"
                      >
                        پرونده بیمار
                      </Link>
                    ) : null}
                  </div>
                ) : (
                  <section className="space-y-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3" data-testid="finance-drawer-op">
                    <h4 className="ds-section-title">
                      {op === "discount" ? "تخفیف" : op === "adjust" ? "تعدیل/اصلاح" : "استرداد تأییدشده"}
                    </h4>
                    <SelectField
                      label="دلیل از پیش‌تعریف‌شده"
                      value={reasonCode}
                      onChange={(e) => setReasonCode(e.target.value)}
                      data-testid="finance-drawer-reason"
                      required
                    >
                      <option value="">انتخاب کنید</option>
                      {reasons.map((r) => (
                        <option key={r.code} value={r.code}>
                          {r.labelFa}
                        </option>
                      ))}
                    </SelectField>
                    {reasonRequiresExplanation(reasons, reasonCode) ? (
                      <TextAreaField
                        label="توضیح الزامی"
                        rows={2}
                        maxLength={400}
                        value={reasonText}
                        onChange={(e) => setReasonText(e.target.value)}
                        data-testid="finance-drawer-reason-text"
                      />
                    ) : (
                      <TextAreaField
                        label="توضیح تکمیلی (اختیاری)"
                        rows={2}
                        maxLength={400}
                        value={reasonText}
                        onChange={(e) => setReasonText(e.target.value)}
                        data-testid="finance-drawer-reason-text"
                      />
                    )}
                    <label className="block text-sm">
                      مبلغ (ریال)
                      <input
                        type="number"
                        min={1}
                        className="ds-input mt-1"
                        value={amount || ""}
                        onChange={(e) => setAmount(Math.max(0, Number(e.target.value) || 0))}
                        data-testid="finance-drawer-amount"
                      />
                    </label>
                    {amount >= MONEY_OUT_APPROVAL_THRESHOLD_IRR && op !== "discount" ? (
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={approved}
                          onChange={(e) => setApproved(e.target.checked)}
                          data-testid="finance-drawer-approve"
                        />
                        تأیید خروج وجه بالای آستانهٔ تصویب
                      </label>
                    ) : null}
                    {error ? <Alert tone="danger">{error}</Alert> : null}
                    <div className="flex flex-wrap gap-2">
                      <Button loading={busy} onClick={() => void submitOp()} data-testid="finance-drawer-submit">
                        تأیید عملیات
                      </Button>
                      <Button variant="ghost" disabled={busy} onClick={resetOp}>
                        انصراف
                      </Button>
                    </div>
                  </section>
                )}
              </section>
            ) : null}
          </div>
        </QueryBoundary>
      )}
    </Dialog>
  );
}
