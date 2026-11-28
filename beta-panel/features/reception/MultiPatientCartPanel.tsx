"use client";

import { useRef, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiJson } from "@/lib/api";
import { allocateFixedDiscountIrr, CheckoutIntentStore } from "@/lib/checkout-intent";
import { FEATURE_FLAGS } from "@/lib/feature-flags";
import { formatCount } from "@/lib/format/numbers";
import { P } from "@/lib/permissions";
import { useSession } from "@/components/session/SessionProvider";
import { buildThermalReceiptText, simulatedThermalPrint } from "@/features/print/thermalReceipt";
import { formatJalaliFromTehranYmd } from "@/lib/format/jalali";
import { tehranTodayYmd } from "@/lib/tehran";
import { insuranceLabel } from "./insurance-catalog";
import type { CartPatientSlot, MultiPatientSettlementResult } from "./multi-patient-cart";

type Props = {
  slots: CartPatientSlot[];
  activePatientId: string | null;
  onSelectPatient: (patientId: string) => void;
  onRemovePatient: (patientId: string) => void;
  onRemoveLine: (patientId: string, lineKey: string) => void;
  onClear: () => void;
};

/**
 * Temporary multi-patient cart (MULTI-01).
 * Settles each patient as an independent invoice — shared settlement stays DISABLED.
 */
export function MultiPatientCartPanel({
  slots,
  activePatientId,
  onSelectPatient,
  onRemovePatient,
  onRemoveLine,
  onClear,
}: Props) {
  const { can } = useSession();
  const intentStores = useRef(new Map<string, CheckoutIntentStore>());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<MultiPatientSettlementResult[]>([]);

  const canCheckout = can(P.financeInvoiceDraft) && can(P.financeInvoicePost) && can(P.financeReceiptRecord);
  const sharedOff = !FEATURE_FLAGS.multiPatientSharedSettlement;

  function storeFor(patientId: string) {
    let store = intentStores.current.get(patientId);
    if (!store) {
      store = new CheckoutIntentStore();
      intentStores.current.set(patientId, store);
    }
    return store;
  }

  async function settleOne(slot: CartPatientSlot): Promise<MultiPatientSettlementResult> {
    const name = `${slot.patient.first_name} ${slot.patient.last_name}`;
    if (slot.lines.length === 0) {
      return { patientId: slot.patient.patient_profile_id, patientName: name, ok: false, message: "خدماتی ندارد" };
    }
    const grosses = slot.lines.map((l) => l.priceIrr);
    const discounts = allocateFixedDiscountIrr(grosses, 0);
    const payable = grosses.reduce((s, g, i) => s + g - discounts[i], 0);
    const lines = slot.lines.map((line, idx) => ({
      service_id: line.serviceId,
      appointment_id: null as string | null,
      description: line.serviceName,
      discount_amount: discounts[idx] ?? 0,
      discount_percent_bps: null as number | null,
      charge_without_service_reason: "desk_manual_charge_authorized",
    }));
    const body = {
      patient_id: slot.patient.patient_profile_id,
      post: true,
      accept_unapplied_credit: false,
      payment_method: "CASH" as const,
      payment_amount_irr: payable,
      lines,
    };
    const intentKey = storeFor(slot.patient.patient_profile_id).keyFor({
      patientId: slot.patient.patient_profile_id,
      lineServiceIds: slot.lines.map((l) => l.serviceId),
      lineAppointmentIds: lines.map((l) => l.appointment_id),
      discountFixed: 0,
      discountBps: 0,
      payMethod: "CASH",
      paymentAmountIrr: payable,
      acceptCredit: false,
      post: true,
    });
    const response = await apiJson<{
      id: string;
      invoice_number: string | null;
      outstanding: number;
      financial_status: string;
    }>("/api/v1/finance/desk-checkout", {
      method: "POST",
      body,
      idempotencyKey: intentKey,
      fallbackMessage: "ثبت صورتحساب ناموفق بود",
    });
    if (!response.ok) {
      return {
        patientId: slot.patient.patient_profile_id,
        patientName: name,
        ok: false,
        message: response.message,
      };
    }
    storeFor(slot.patient.patient_profile_id).rotate();
    return {
      patientId: slot.patient.patient_profile_id,
      patientName: name,
      ok: true,
      message: response.data.financial_status,
      invoiceId: response.data.id,
      invoiceNumber: response.data.invoice_number,
      outstanding: response.data.outstanding,
    };
  }

  async function settleSeparately() {
    if (busy || !canCheckout) return;
    setBusy(true);
    setError(null);
    const settled: MultiPatientSettlementResult[] = [];
    for (const slot of slots) {
      if (slot.lines.length === 0) continue;
      settled.push(await settleOne(slot));
    }
    setResults(settled);
    setBusy(false);
    if (settled.every((r) => r.ok)) onClear();
  }

  async function batchPrint() {
    const okResults = results.filter((r) => r.ok);
    if (!okResults.length) return;
    const texts = okResults.map((r) => {
      const slot = slots.find((s) => s.patient.patient_profile_id === r.patientId);
      return buildThermalReceiptText({
        clinicName: "کلینیک نمونه",
        invoiceNumber: r.invoiceNumber ?? r.invoiceId ?? "—",
        jalaliDate: formatJalaliFromTehranYmd(tehranTodayYmd()),
        patientDisplay: r.patientName,
        lines: (slot?.lines ?? []).map((l) => ({ description: l.serviceName, amountIrr: l.priceIrr })),
        totalPayableIrr: (slot?.lines ?? []).reduce((s, l) => s + l.priceIrr, 0),
        methodLabel: "نقدی (جداگانه)",
        synthetic: true,
      });
    });
    await simulatedThermalPrint(texts.join("\n\n========\n\n"));
  }

  if (!FEATURE_FLAGS.multiPatientCart) return null;

  return (
    <section className="ds-card space-y-3 p-4" aria-label="سبد چندبیمار موقت" data-testid="multi-patient-cart">
      <div>
        <h2 className="ds-section-title">سبد چندبیمار (موقت)</h2>
        <p className="ds-hint">
          هر بیمار صورتحساب مستقل دارد. تسویهٔ مشترک تک‌ورودی{" "}
          {sharedOff ? "غیرفعال است" : "فعال است"} تا تصویب ACR.
        </p>
      </div>

      {slots.length === 0 ? (
        <p className="ds-hint">بیماری به سبد اضافه نشده است.</p>
      ) : (
        <ul className="space-y-3" data-testid="multi-patient-slots">
          {slots.map((slot) => {
            const active = slot.patient.patient_profile_id === activePatientId;
            const total = slot.lines.reduce((s, l) => s + l.priceIrr, 0);
            return (
              <li
                key={slot.key}
                className={`rounded-[var(--ds-radius-md)] border px-3 py-2 ${
                  active ? "border-[var(--ds-primary)] bg-[var(--ds-primary-soft)]" : "border-[var(--ds-border)]"
                }`}
                data-testid="multi-patient-slot"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <button
                    type="button"
                    className="text-start font-medium hover:underline"
                    onClick={() => onSelectPatient(slot.patient.patient_profile_id)}
                    data-testid="multi-patient-select"
                  >
                    {slot.patient.first_name} {slot.patient.last_name}
                  </button>
                  <button
                    type="button"
                    className="text-xs text-[var(--ds-danger)]"
                    onClick={() => onRemovePatient(slot.patient.patient_profile_id)}
                    data-testid="multi-patient-remove"
                  >
                    حذف بیمار
                  </button>
                </div>
                <p className="text-xs text-[var(--ds-text-muted)]">{insuranceLabel(slot.insuranceCode)}</p>
                <ul className="mt-2 space-y-1 text-sm">
                  {slot.lines.map((line) => (
                    <li key={line.key} className="flex justify-between gap-2">
                      <span className="truncate">{line.serviceName}</span>
                      <span className="flex items-center gap-2">
                        <span className="tabular-nums">{formatCount(line.priceIrr)}</span>
                        <button
                          type="button"
                          className="text-xs text-[var(--ds-danger)]"
                          onClick={() => onRemoveLine(slot.patient.patient_profile_id, line.key)}
                        >
                          حذف
                        </button>
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-1 text-sm font-semibold tabular-nums">{formatCount(total)} ریال · {slot.lines.length} خدمت</p>
              </li>
            );
          })}
        </ul>
      )}

      <div className="flex flex-wrap gap-2 border-t border-[var(--ds-border)] pt-3">
        <Button
          disabled={!canCheckout || busy || slots.every((s) => s.lines.length === 0)}
          loading={busy}
          onClick={() => void settleSeparately()}
          data-testid="multi-patient-settle-separate"
        >
          تسویهٔ جداگانهٔ هر بیمار
        </Button>
        <Button
          variant="ghost"
          disabled
          title="تا تصویب ACR و فعال‌سازی پرچم CLINIC_MULTI_PATIENT_SETTLEMENT غیرفعال است"
          data-testid="multi-patient-settle-shared"
        >
          تسویهٔ مشترک (غیرفعال)
        </Button>
      </div>

      {error ? <Alert tone="danger">{error}</Alert> : null}

      {results.length > 0 ? (
        <div className="space-y-2 rounded-[var(--ds-radius-md)] border border-[var(--ds-border)] p-3" data-testid="multi-patient-results">
          <h3 className="ds-section-title">نتایج گروهی</h3>
          <ul className="space-y-1 text-sm">
            {results.map((r) => (
              <li key={r.patientId} className="flex flex-wrap items-center gap-2">
                <StatusBadge tone={r.ok ? "ok" : "danger"}>{r.ok ? "ثبت شد" : "خطا"}</StatusBadge>
                <span>{r.patientName}</span>
                <span className="tabular-nums text-[var(--ds-text-muted)]">
                  {r.invoiceNumber ?? r.message}
                </span>
              </li>
            ))}
          </ul>
          <Button variant="ghost" size="sm" onClick={() => void batchPrint()} data-testid="multi-patient-batch-print">
            چاپ دسته‌ای شبیه‌سازی‌شده
          </Button>
        </div>
      ) : null}
    </section>
  );
}
