"use client";

import { Alert } from "@/components/feedback/Alert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useSession } from "@/components/session/SessionProvider";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { buildQuery } from "@/lib/api";
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

export function FinanceView() {
  const { can, status } = useSession();
  const [refresh, setRefresh] = useState(0);
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

  return (
    <main className="space-y-6" data-testid="finance-page">
      <PageHeader
        title="امور مالی"
        description="صورتحساب‌های ثبت‌شده، وضعیت پرداخت و خلاصهٔ مجاز. پرداخت زنده و بیمه فعال نیست."
        actions={
          <Button variant="ghost" icon="refresh" onClick={() => setRefresh((v) => v + 1)} data-testid="finance-refresh">
            به‌روزرسانی
          </Button>
        }
      />
      {summary.error ? <Alert>{summary.error.message}</Alert> : null}
      {invoices.error ? <Alert testId="finance-error">{invoices.error.message}</Alert> : null}

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
    </main>
  );
}
