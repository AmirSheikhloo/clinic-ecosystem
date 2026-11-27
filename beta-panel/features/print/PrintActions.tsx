"use client";

import { useMemo, useRef, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { apiJson } from "@/lib/api";
import { createPrintJobStore, reprintJob, submitBatchPrintJobs, submitPrintJob } from "./printJobs";
import type { ThermalReceiptInput, ThermalWidth } from "./thermalReceipt";
import {
  canAutoPrint,
  loadWorkstationPrinterProfile,
  markDisconnected,
  markEnrolledAfterTestPrint,
  saveWorkstationPrinterProfile,
  type WorkstationPrinterProfile,
} from "./workstationPrinter";

export type PrintableInvoiceRef = {
  invoiceId: string;
  invoiceNumber: string;
  patientDisplay: string;
  jalaliDate: string;
  lines: Array<{ description: string; amountIrr: number; quantity?: number }>;
  discountIrr?: number;
  totalPayableIrr: number;
  paidIrr?: number;
  methodLabel?: string;
  financialStatus?: string;
  courseSessionHint?: string;
  nextHint?: string;
};

type SnapshotResponse = {
  invoice_id: string;
  invoice_number: string;
  jalali_date: string;
  patient_display: string;
  lines: Array<{ description: string; amount_irr: number; quantity_scaled?: number }>;
  discount_irr: number;
  total_payable_irr: number;
  paid_irr: number;
  method_label: string | null;
  financial_status: string;
  course_session_hint: string | null;
  next_suggested_hint: string | null;
  synthetic: boolean;
};

type Props = {
  invoices: PrintableInvoiceRef[];
  /** When set, prefer server immutable snapshot over client draft fields. */
  preferServerSnapshot?: boolean;
};

function toThermalInput(
  inv: PrintableInvoiceRef,
  widthMm: ThermalWidth,
  extras?: Partial<ThermalReceiptInput>,
): ThermalReceiptInput {
  return {
    clinicName: "کلینیک نمونه",
    invoiceNumber: inv.invoiceNumber,
    jalaliDate: inv.jalaliDate,
    patientDisplay: inv.patientDisplay,
    lines: inv.lines,
    discountIrr: inv.discountIrr,
    totalPayableIrr: inv.totalPayableIrr,
    paidIrr: inv.paidIrr,
    methodLabel: inv.methodLabel,
    financialStatus: inv.financialStatus,
    courseSessionHint: inv.courseSessionHint,
    nextHint: inv.nextHint,
    widthMm,
    synthetic: true,
    ...extras,
  };
}

async function fetchServerSnapshot(invoiceId: string): Promise<PrintableInvoiceRef | null> {
  const response = await apiJson<SnapshotResponse>(
    `/api/v1/finance/invoices/${invoiceId}/print-snapshot`,
    { fallbackMessage: "بازیابی تصویر ثابت فاکتور ناموفق بود" },
  );
  if (!response.ok) return null;
  const s = response.data;
  return {
    invoiceId: s.invoice_id,
    invoiceNumber: s.invoice_number,
    jalaliDate: s.jalali_date,
    patientDisplay: s.patient_display,
    lines: s.lines.map((l) => ({
      description: l.description,
      amountIrr: l.amount_irr,
      quantity: l.quantity_scaled,
    })),
    discountIrr: s.discount_irr,
    totalPayableIrr: s.total_payable_irr,
    paidIrr: s.paid_irr,
    methodLabel: s.method_label ?? undefined,
    financialStatus: s.financial_status,
    courseSessionHint: s.course_session_hint ?? undefined,
    nextHint: s.next_suggested_hint ?? undefined,
  };
}

/** Thermal print / reprint / batch / workstation enrollment — no checkout mutation. */
export function PrintActions({ invoices, preferServerSnapshot = true }: Props) {
  const storeRef = useRef(createPrintJobStore());
  const [profile, setProfile] = useState<WorkstationPrinterProfile>(() =>
    loadWorkstationPrinterProfile(),
  );
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const enrolled = profile.health === "ENROLLED";

  const widthLabel = useMemo(
    () => (profile.widthMm === 58 ? "۵۸ میلی‌متر" : "۸۰ میلی‌متر (پیش‌فرض)"),
    [profile.widthMm],
  );

  async function resolveInvoice(inv: PrintableInvoiceRef): Promise<PrintableInvoiceRef> {
    if (!preferServerSnapshot) return inv;
    const snap = await fetchServerSnapshot(inv.invoiceId);
    return snap ?? inv;
  }

  async function runTestPrint() {
    setBusy(true);
    setError(null);
    setMessage(null);
    const testSnapshot = toThermalInput(
      {
        invoiceId: "test",
        invoiceNumber: "TEST",
        jalaliDate: "—",
        patientDisplay: "آزمایش چاپ",
        lines: [{ description: "چاپ آزمایشی", amountIrr: 0 }],
        totalPayableIrr: 0,
        financialStatus: "TEST",
      },
      profile.widthMm,
    );
    const job = await submitPrintJob({
      store: storeRef.current,
      snapshot: testSnapshot,
      invoiceId: "test",
      workstationId: profile.workstationId,
      kind: "TEST",
      scenario: profile.printerName.trim() ? "success" : "disconnected",
    });
    setPreview(job.renderedText);
    setLastJobId(job.jobId);
    if (job.status === "SPOOLED") {
      const next = markEnrolledAfterTestPrint(
        { ...profile, printerName: profile.printerName || "Simulated Thermal" },
        job.jobId,
      );
      saveWorkstationPrinterProfile(next);
      setProfile(next);
      setMessage(`چاپ آزمایشی موفق (شبیه‌سازی) · کار ${job.jobId}`);
    } else {
      const next = markDisconnected(profile);
      saveWorkstationPrinterProfile(next);
      setProfile(next);
      setError(job.adapterDetail);
    }
    setBusy(false);
  }

  async function printOne(inv: PrintableInvoiceRef, asReprint = false) {
    setBusy(true);
    setError(null);
    setMessage(null);
    const resolved = await resolveInvoice(inv);
    const snapshot = toThermalInput(resolved, profile.widthMm);
    const job = await submitPrintJob({
      store: storeRef.current,
      snapshot,
      invoiceId: resolved.invoiceId,
      workstationId: profile.workstationId,
      kind: asReprint ? "REPRINT" : "RECEIPT",
      autoIntentKey: asReprint ? undefined : `auto:${resolved.invoiceId}`,
      scenario: profile.health === "DISCONNECTED" ? "disconnected" : "success",
    });
    setPreview(job.renderedText);
    setLastJobId(job.jobId);
    if (job.status === "SPOOLED") {
      setMessage(`چاپ ${asReprint ? "مجدد" : ""} ثبت شد · ${job.jobId} — بدون تغییر مالی`);
    } else {
      setError(job.adapterDetail);
    }
    setBusy(false);
  }

  async function printAll() {
    setBusy(true);
    setError(null);
    setMessage(null);
    const resolved = [];
    for (const inv of invoices) {
      resolved.push(await resolveInvoice(inv));
    }
    const { batchId, jobs } = await submitBatchPrintJobs(
      storeRef.current,
      resolved.map((inv) => ({
        snapshot: toThermalInput(inv, profile.widthMm),
        invoiceId: inv.invoiceId,
        workstationId: profile.workstationId,
      })),
      profile.health === "DISCONNECTED" ? "disconnected" : "success",
    );
    setPreview(jobs.map((j) => j.renderedText).join("\n\n=== برش ===\n\n"));
    setLastJobId(jobs.at(-1)?.jobId ?? null);
    const failed = jobs.filter((j) => j.status !== "SPOOLED");
    if (failed.length) {
      setError(`دسته ${batchId}: ${failed.length} مورد ناموفق — پرداخت تکرار نشده`);
    } else {
      setMessage(`چاپ دسته‌ای ${jobs.length} رسید مستقل · ${batchId}`);
    }
    setBusy(false);
  }

  async function doReprint() {
    if (!lastJobId) return;
    setBusy(true);
    setError(null);
    try {
      const job = await reprintJob(storeRef.current, lastJobId);
      setPreview(job.renderedText);
      setLastJobId(job.jobId);
      setMessage(`چاپ مجدد از تصویر ثابت · ${job.jobId} — صندوق دست‌نخورده`);
    } catch {
      setError("کار چاپ برای تجدید یافت نشد");
    }
    setBusy(false);
  }

  function updateProfile(patch: Partial<WorkstationPrinterProfile>) {
    const next = { ...profile, ...patch };
    saveWorkstationPrinterProfile(next);
    setProfile(next);
  }

  if (invoices.length === 0) return null;

  return (
    <section
      className="space-y-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3"
      data-testid="print-actions"
      aria-label="چاپ حرارتی"
    >
      <div>
        <h3 className="text-sm font-semibold">چاپ رسید حرارتی</h3>
        <p className="ds-hint text-xs">
          عرض {widthLabel} · آداپتر شبیه‌سازی‌شده · چاپ مجدد پرداخت را تکرار نمی‌کند
          {canAutoPrint(profile) ? " · چاپ خودکار پس از ثبت فعال است" : ""}
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <label className="block text-xs">
          نام چاپگر ایستگاه
          <input
            className="ds-input mt-1"
            value={profile.printerName}
            onChange={(e) => updateProfile({ printerName: e.target.value })}
            data-testid="printer-name"
            placeholder="Simulated Thermal"
          />
        </label>
        <label className="block text-xs">
          عرض رول
          <select
            className="ds-input mt-1"
            value={profile.widthMm}
            onChange={(e) =>
              updateProfile({ widthMm: Number(e.target.value) === 58 ? 58 : 80 })
            }
            data-testid="printer-width"
          >
            <option value={80}>۸۰ میلی‌متر (پیش‌فرض)</option>
            <option value={58}>۵۸ میلی‌متر</option>
          </select>
        </label>
      </div>

      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={profile.autoPrintAfterCommit}
          onChange={(e) => updateProfile({ autoPrintAfterCommit: e.target.checked })}
          data-testid="printer-auto"
        />
        چاپ خودکار پس از ثبت (فقط پس از ثبت و چاپ آزمایشی موفق)
      </label>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="ghost"
          disabled={busy}
          onClick={() => void runTestPrint()}
          data-testid="printer-test"
        >
          ثبت و چاپ آزمایشی
        </Button>
        <Button
          type="button"
          variant="primary"
          disabled={busy || !enrolled}
          onClick={() => void printOne(invoices[0])}
          data-testid="printer-print"
        >
          چاپ
        </Button>
        {invoices.length > 1 ? (
          <Button
            type="button"
            variant="primary"
            disabled={busy || !enrolled}
            onClick={() => void printAll()}
            data-testid="printer-print-all"
          >
            چاپ همه
          </Button>
        ) : null}
        <Button
          type="button"
          variant="ghost"
          disabled={busy || !lastJobId}
          onClick={() => void doReprint()}
          data-testid="printer-reprint"
        >
          چاپ مجدد
        </Button>
      </div>

      {!enrolled ? (
        <p className="ds-hint text-xs" data-testid="printer-enroll-hint">
          ابتدا چاپ آزمایشی را با موفقیت انجام دهید تا چاپ عادی بدون دیالوگ دستگاه مجاز شود.
        </p>
      ) : null}

      {message ? (
        <p className="text-xs text-[var(--ds-success)]" data-testid="printer-status">
          {message}
        </p>
      ) : null}
      {error ? <Alert testId="printer-error">{error}</Alert> : null}
      {preview ? (
        <pre
          className="max-h-48 overflow-auto rounded bg-[var(--ds-surface-muted)] p-2 text-[11px] leading-relaxed"
          dir="rtl"
          data-testid="printer-preview"
        >
          {preview}
        </pre>
      ) : null}
    </section>
  );
}
