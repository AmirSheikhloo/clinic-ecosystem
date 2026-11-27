"use client";

import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson, buildQuery } from "@/lib/api";
import { tehranDayBoundsUtc, tehranTodayYmd } from "@/lib/client";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useApiQuery } from "@/lib/use-api-query";
import Link from "next/link";
import { useState } from "react";

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

type InvoiceList = { items: InvoiceRow[] };

type FinanceSummary = {
  posted_invoices: number;
  draft_invoices: number;
  receipt_count: number;
  receipt_total_irr: number;
  refund_count: number;
  refund_total_irr: number;
  net_collected_irr: number;
};

type InvoiceDetail = {
  id: string;
  status: string;
  lines: Array<{ id: string; description: string; patient_payable_amount: number }>;
  allocations: Array<{
    id: string;
    receipt_id: string;
    invoice_line_id: string;
    allocation_kind: string;
    amount_irr: number;
    payment_method: string;
  }>;
  outstanding: number;
  allocated_total: number;
  financial_status: string;
};

export function FinanceView() {
  const { can, status } = useSession();
  const [refresh, setRefresh] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [adjDelta, setAdjDelta] = useState(-10000);
  const [busy, setBusy] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const allowed = can(P.financeInvoiceView);
  const today = tehranTodayYmd();
  const bounds = tehranDayBoundsUtc(today);
  const summary = useApiQuery<FinanceSummary>(
    status === "ready" && can(P.financeSummary)
      ? `/api/v1/finance/summary${buildQuery({ start_at_utc: bounds.start, end_at_utc: bounds.end })}`
      : null,
    "بارگذاری خلاصه مالی ناموفق بود",
    refresh,
  );
  const invoices = useApiQuery<InvoiceList>(
    status === "ready" && allowed ? "/api/v1/finance/invoices?limit=40" : null,
    "بارگذاری صورتحساب‌ها ناموفق بود",
    refresh,
  );
  const detail = useApiQuery<InvoiceDetail>(
    status === "ready" && allowed && selectedId ? `/api/v1/finance/invoices/${selectedId}` : null,
    "بارگذاری جزئیات صورتحساب ناموفق بود",
    refresh,
  );

  if (status === "loading") return <PageSkeleton />;
  if (!allowed && !can(P.financeSummary)) {
    return (
      <main data-testid="finance-page">
        <PageHeader title="امور مالی" description="مشاهدهٔ این بخش نیازمند مجوز مالی است." />
        <EmptyState title="دسترسی ندارید" description="مجوز FINANCE لازم است." />
      </main>
    );
  }

  const tone = (fs: string) => (fs === "PAID" ? "ok" : fs === "PARTIAL" ? "warn" : "danger");

  async function applyAdjustment() {
    if (!detail.data || !can(P.financeAdjustment) || detail.data.lines.length === 0) return;
    setBusy(true);
    setActionMsg(null);
    const result = await apiJson("/api/v1/finance/adjustments", {
      method: "POST",
      body: {
        invoice_id: detail.data.id,
        invoice_line_id: detail.data.lines[0].id,
        adjustment_kind: adjDelta < 0 ? "POST_PAYMENT_DISCOUNT" : "CORRECTION",
        patient_delta_irr: adjDelta,
        reason_code: "UI_ADJUSTMENT",
        reason_text: "تعدیل از فضای مالی",
      },
    });
    setBusy(false);
    if (!result.ok) {
      setActionMsg(result.message);
      return;
    }
    setActionMsg("تعدیل ثبت شد");
    setRefresh((v) => v + 1);
  }

  async function applyRefund() {
    if (!detail.data || !can(P.financeRefund)) return;
    const apply = detail.data.allocations.find((a) => a.allocation_kind === "APPLY");
    if (!apply) {
      setActionMsg("تخصیص قابل استرداد نیست");
      return;
    }
    setBusy(true);
    setActionMsg(null);
    const result = await apiJson("/api/v1/finance/refunds", {
      method: "POST",
      body: {
        original_receipt_id: apply.receipt_id,
        invoice_id: detail.data.id,
        invoice_line_id: apply.invoice_line_id,
        original_allocation_id: apply.id,
        amount_irr: Math.min(apply.amount_irr, 10_000),
        refund_method: apply.payment_method === "POS" ? "POS" : "CASH",
        reason_code: "UI_REFUND",
        idempotency_key: `ui-refund-${apply.id}-${Date.now()}`,
      },
    });
    setBusy(false);
    if (!result.ok) {
      setActionMsg(result.message);
      return;
    }
    setActionMsg("استرداد ثبت شد");
    setRefresh((v) => v + 1);
  }

  return (
    <main className="space-y-6" data-testid="finance-page">
      <PageHeader
        title="امور مالی"
        description="صورتحساب، تخفیف پس از پرداخت، استرداد و مانده. پرداخت زنده و بیمه فعال نیست."
        actions={
          <Button variant="ghost" icon="refresh" onClick={() => setRefresh((v) => v + 1)} data-testid="finance-refresh">
            به‌روزرسانی
          </Button>
        }
      />
      {summary.error ? <Alert>{summary.error.message}</Alert> : null}
      {invoices.error ? <Alert testId="finance-error">{invoices.error.message}</Alert> : null}
      {actionMsg ? <Alert testId="finance-action-msg">{actionMsg}</Alert> : null}

      {can(P.financeSummary) && summary.data ? (
        <section className="ds-metric-grid" aria-label="خلاصه مالی امروز" data-testid="finance-summary">
          <div className="ds-card p-4">
            <p className="text-xs text-[var(--ds-text-muted)]">صورتحساب ثبت‌شده</p>
            <p className="text-xl font-semibold tabular-nums">{formatCount(summary.data.posted_invoices)}</p>
          </div>
          <div className="ds-card p-4">
            <p className="text-xs text-[var(--ds-text-muted)]">رسیدها</p>
            <p className="text-xl font-semibold tabular-nums">{formatCount(summary.data.receipt_count)}</p>
          </div>
          <div className="ds-card p-4">
            <p className="text-xs text-[var(--ds-text-muted)]">خالص دریافتی (ریال)</p>
            <p className="text-xl font-semibold tabular-nums" data-testid="finance-net">
              {formatCount(summary.data.net_collected_irr)}
            </p>
          </div>
          <div className="ds-card p-4">
            <p className="text-xs text-[var(--ds-text-muted)]">استردادها</p>
            <p className="text-xl font-semibold tabular-nums">{formatCount(summary.data.refund_count)}</p>
          </div>
        </section>
      ) : null}

      {allowed ? (
        <section aria-label="فهرست صورتحساب" data-testid="finance-invoices">
          {!invoices.loading && (invoices.data?.items.length ?? 0) === 0 ? (
            <EmptyState title="صورتحسابی نیست" description="هنوز صورتحسابی در پایگاه نمایشی ثبت نشده است." />
          ) : (
            <ul className="space-y-2">
              {(invoices.data?.items ?? []).map((inv) => (
                <li key={inv.id} className="ds-card flex flex-wrap items-center justify-between gap-3 p-4" data-testid="finance-invoice">
                  <div>
                    <p className="font-medium tabular-nums">{inv.invoice_number ?? inv.id.slice(0, 8)}</p>
                    <p className="text-xs text-[var(--ds-text-muted)]">
                      قابل پرداخت {formatCount(inv.patient_payable_total)} · پرداخت‌شده {formatCount(inv.allocated_total)} · مانده{" "}
                      {formatCount(inv.outstanding)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge tone={tone(inv.financial_status)}>{inv.financial_status}</StatusBadge>
                    <Button
                      variant="ghost"
                      onClick={() => setSelectedId(inv.id)}
                      data-testid="finance-open-invoice"
                    >
                      جزئیات
                    </Button>
                    <Link href={`/patients/${inv.patient_id}`} className="text-sm text-[var(--ds-accent)]">
                      پرونده بیمار
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {selectedId && detail.data ? (
        <section className="ds-card space-y-4 p-5" data-testid="finance-invoice-detail">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="ds-section-title">جزئیات صورتحساب</h2>
            <StatusBadge tone={tone(detail.data.financial_status)}>{detail.data.financial_status}</StatusBadge>
          </div>
          <ul className="space-y-1 text-sm">
            {detail.data.lines.map((ln) => (
              <li key={ln.id} className="flex justify-between gap-2">
                <span>{ln.description}</span>
                <span className="tabular-nums">{formatCount(ln.patient_payable_amount)}</span>
              </li>
            ))}
          </ul>
          <p className="text-sm tabular-nums">
            پرداخت‌شده {formatCount(detail.data.allocated_total)} · مانده {formatCount(detail.data.outstanding)}
          </p>

          {can(P.financeAdjustment) && detail.data.status === "POSTED" ? (
            <div className="flex flex-wrap items-end gap-2 border-t border-[var(--ds-border)] pt-3">
              <label className="text-sm">
                تعدیل (ریال، منفی = کاهش بدهی)
                <input
                  type="number"
                  className="ds-input mt-1"
                  value={adjDelta}
                  onChange={(e) => setAdjDelta(Number(e.target.value) || 0)}
                  data-testid="finance-adj-delta"
                />
              </label>
              <Button loading={busy} onClick={() => void applyAdjustment()} data-testid="finance-adjust">
                ثبت تعدیل
              </Button>
            </div>
          ) : null}

          {can(P.financeRefund) && detail.data.allocations.some((a) => a.allocation_kind === "APPLY") ? (
            <div className="border-t border-[var(--ds-border)] pt-3">
              <Button loading={busy} variant="danger" onClick={() => void applyRefund()} data-testid="finance-refund">
                استرداد جزئی (تا 10,000 ریال)
              </Button>
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
