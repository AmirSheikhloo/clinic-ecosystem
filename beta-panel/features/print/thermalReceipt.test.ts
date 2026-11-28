import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildThermalReceiptText,
  browserPrintFallbackDisclosure,
  qzHardwarePathBlocked,
  simulatedThermalPrint,
} from "./thermalReceipt";
import {
  createPrintJobStore,
  recoverPrintJob,
  reprintJob,
  submitBatchPrintJobs,
  submitPrintJob,
} from "./printJobs";
import {
  blankProfile,
  canAutoPrint,
  markEnrolledAfterTestPrint,
} from "./workstationPrinter";

const baseSnapshot = {
  clinicName: "کلینیک نمونه",
  invoiceNumber: "INV-1",
  jalaliDate: "1404/09/06",
  patientDisplay: "مریم احمدی",
  lines: [{ description: "ویزیت پوست", amountIrr: 500_000, quantity: 1 }],
  totalPayableIrr: 500_000,
  paidIrr: 500_000,
  methodLabel: "نقدی",
  financialStatus: "PAID",
};

describe("thermalReceipt", () => {
  it("builds synthetic 80mm receipt without national id", () => {
    const text = buildThermalReceiptText(baseSnapshot);
    assert.match(text, /مریم احمدی/);
    assert.match(text, /نمونه مصنوعی/);
    assert.doesNotMatch(text, /کد ملی/);
    assert.match(text, /ریال/);
  });

  it("supports optional 58mm width with shorter rule", () => {
    const text80 = buildThermalReceiptText({ ...baseSnapshot, widthMm: 80 });
    const text58 = buildThermalReceiptText({ ...baseSnapshot, widthMm: 58 });
    assert.ok(text58.split("\n")[1]!.length < text80.split("\n")[1]!.length);
  });

  it("includes course session and suggested next visit disclaimer", () => {
    const text = buildThermalReceiptText({
      ...baseSnapshot,
      courseSessionHint: "جلسه 4 از 10",
      nextHint: "پیشنهاد مراجعه بعدی: ۱۴۰۴/۱۰/۰۶",
    });
    assert.match(text, /جلسه 4 از 10/);
    assert.match(text, /نوبت قطعی نیست/);
  });

  it("blocks privacy-unsafe national-id phrasing", () => {
    assert.throws(
      () =>
        buildThermalReceiptText({
          ...baseSnapshot,
          patientDisplay: "مریم · کد ملی ۱۲۳",
        }),
      /privacy_blocked/,
    );
  });

  it("simulated adapter does not claim hardware", async () => {
    const result = await simulatedThermalPrint("x");
    assert.equal(result.mode, "simulated");
    assert.equal(result.ok, true);
    assert.equal(result.hardwareClaim, "none");
    assert.equal(result.status, "SPOOLED_SIMULATED");
  });

  it("failed/unknown/disconnected scenarios stay honest", async () => {
    const failed = await simulatedThermalPrint("x", { scenario: "failed" });
    assert.equal(failed.ok, false);
    assert.equal(failed.status, "FAILED");
    const unknown = await simulatedThermalPrint("x", { scenario: "unknown" });
    assert.equal(unknown.status, "UNKNOWN");
    const disc = await simulatedThermalPrint("x", { scenario: "disconnected" });
    assert.equal(disc.ok, false);
    assert.match(disc.detail, /قطع/);
  });

  it("QZ and browser fallback disclose blockers", () => {
    assert.equal(qzHardwarePathBlocked().status, "BLOCKED");
    assert.equal(browserPrintFallbackDisclosure().hardwareClaim, "browser_dialog");
  });
});

describe("printJobs", () => {
  it("reprint uses snapshot and does not require new checkout", async () => {
    const store = createPrintJobStore();
    const first = await submitPrintJob({
      store,
      snapshot: { ...baseSnapshot, widthMm: 80 },
      invoiceId: "inv-1",
      workstationId: "ws-1",
    });
    assert.equal(first.status, "SPOOLED");
    const reprint = await reprintJob(store, first.jobId);
    assert.equal(reprint.kind, "REPRINT");
    assert.equal(reprint.snapshot.invoiceNumber, "INV-1");
    assert.match(reprint.renderedText, /چاپ مجدد/);
    assert.notEqual(reprint.jobId, first.jobId);
  });

  it("rejects duplicate auto-print intent (refresh)", async () => {
    const store = createPrintJobStore();
    const a = await submitPrintJob({
      store,
      snapshot: baseSnapshot,
      invoiceId: "inv-1",
      workstationId: "ws-1",
      autoIntentKey: "auto:inv-1",
    });
    assert.equal(a.status, "SPOOLED");
    const b = await submitPrintJob({
      store,
      snapshot: baseSnapshot,
      invoiceId: "inv-1",
      workstationId: "ws-1",
      autoIntentKey: "auto:inv-1",
    });
    assert.equal(b.status, "FAILED");
    assert.match(b.adapterDetail, /تکرار خودکار/);
  });

  it("batch prints independent patient receipts", async () => {
    const store = createPrintJobStore();
    const { batchId, jobs } = await submitBatchPrintJobs(store, [
      {
        snapshot: { ...baseSnapshot, invoiceNumber: "INV-A", patientDisplay: "بیمار الف" },
        invoiceId: "a",
        workstationId: "ws-1",
      },
      {
        snapshot: { ...baseSnapshot, invoiceNumber: "INV-B", patientDisplay: "بیمار ب" },
        invoiceId: "b",
        workstationId: "ws-1",
      },
    ]);
    assert.ok(batchId);
    assert.equal(jobs.length, 2);
    assert.equal(jobs[0]!.invoiceNumber, "INV-A");
    assert.equal(jobs[1]!.invoiceNumber, "INV-B");
    assert.notEqual(jobs[0]!.jobId, jobs[1]!.jobId);
  });

  it("recovers UNKNOWN without finance mutation side-effects", async () => {
    const store = createPrintJobStore();
    const unknown = await submitPrintJob({
      store,
      snapshot: baseSnapshot,
      invoiceId: "inv-1",
      workstationId: "ws-1",
      scenario: "unknown",
    });
    assert.equal(unknown.status, "UNKNOWN");
    const recovered = await recoverPrintJob(store, unknown.jobId, "retry", "success");
    assert.equal(recovered.status, "SPOOLED");
    assert.equal(recovered.snapshot.invoiceNumber, "INV-1");
  });
});

describe("workstationPrinter", () => {
  it("requires enrollment + test print before auto-print", () => {
    const blank = blankProfile("ws-x");
    assert.equal(canAutoPrint(blank), false);
    const enrolled = markEnrolledAfterTestPrint(
      { ...blank, printerName: "Sim", autoPrintAfterCommit: true },
      "job-1",
    );
    assert.equal(canAutoPrint(enrolled), true);
  });
});
