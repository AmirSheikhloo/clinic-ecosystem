/**
 * Print-job identity separate from checkout idempotency.
 * Reprint never re-runs booking, invoice posting, or payment.
 */

import {
  buildThermalReceiptText,
  simulatedThermalPrint,
  type PrintAdapterResult,
  type SimulatedPrintScenario,
  type ThermalReceiptInput,
  type ThermalWidth,
} from "./thermalReceipt";

export type PrintJobStatus =
  | "QUEUED"
  | "SPOOLED"
  | "FAILED"
  | "UNKNOWN"
  | "CANCELLED";

export type PrintJobKind = "RECEIPT" | "TEST" | "BATCH_ITEM" | "REPRINT";

export type PrintJobRecord = {
  jobId: string;
  kind: PrintJobKind;
  status: PrintJobStatus;
  invoiceId: string;
  invoiceNumber: string;
  patientDisplay: string;
  workstationId: string;
  widthMm: ThermalWidth;
  /** Snapshot payload used for this job — immutable for reprints. */
  snapshot: ThermalReceiptInput;
  renderedText: string;
  createdAtIso: string;
  updatedAtIso: string;
  attempt: number;
  parentJobId?: string;
  batchId?: string;
  adapterDetail: string;
  hardwareClaim: PrintAdapterResult["hardwareClaim"];
};

export type PrintJobStore = {
  jobs: Map<string, PrintJobRecord>;
  /** Prevents duplicate automatic print on refresh for the same invoice+intent. */
  autoPrintedIntents: Set<string>;
};

export function createPrintJobStore(): PrintJobStore {
  return { jobs: new Map(), autoPrintedIntents: new Set() };
}

function newJobId(): string {
  return `pj-${crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`}`;
}

export type SubmitPrintArgs = {
  store: PrintJobStore;
  snapshot: ThermalReceiptInput;
  invoiceId: string;
  workstationId: string;
  kind?: PrintJobKind;
  parentJobId?: string;
  batchId?: string;
  autoIntentKey?: string;
  scenario?: SimulatedPrintScenario;
};

export async function submitPrintJob(args: SubmitPrintArgs): Promise<PrintJobRecord> {
  const {
    store,
    snapshot,
    invoiceId,
    workstationId,
    kind = "RECEIPT",
    parentJobId,
    batchId,
    autoIntentKey,
    scenario = "success",
  } = args;

  if (autoIntentKey && store.autoPrintedIntents.has(autoIntentKey)) {
    const dupId = newJobId();
    const now = new Date().toISOString();
    const renderedText = buildThermalReceiptText(snapshot);
    const dup: PrintJobRecord = {
      jobId: dupId,
      kind,
      status: "FAILED",
      invoiceId,
      invoiceNumber: snapshot.invoiceNumber,
      patientDisplay: snapshot.patientDisplay,
      workstationId,
      widthMm: snapshot.widthMm === 58 ? 58 : 80,
      snapshot,
      renderedText,
      createdAtIso: now,
      updatedAtIso: now,
      attempt: 1,
      parentJobId,
      batchId,
      adapterDetail: "تکرار خودکار چاپ پس از تازه‌سازی صفحه رد شد",
      hardwareClaim: "none",
    };
    store.jobs.set(dupId, dup);
    return dup;
  }

  const jobId = newJobId();
  const now = new Date().toISOString();
  const renderedText = buildThermalReceiptText(snapshot);
  const queued: PrintJobRecord = {
    jobId,
    kind,
    status: "QUEUED",
    invoiceId,
    invoiceNumber: snapshot.invoiceNumber,
    patientDisplay: snapshot.patientDisplay,
    workstationId,
    widthMm: snapshot.widthMm === 58 ? 58 : 80,
    snapshot,
    renderedText,
    createdAtIso: now,
    updatedAtIso: now,
    attempt: 1,
    parentJobId,
    batchId,
    adapterDetail: "در صف شبیه‌سازی",
    hardwareClaim: "none",
  };
  store.jobs.set(jobId, queued);

  const result = await simulatedThermalPrint(renderedText, { jobId, scenario });
  const status: PrintJobStatus =
    result.status === "SPOOLED_SIMULATED"
      ? "SPOOLED"
      : result.status === "UNKNOWN"
        ? "UNKNOWN"
        : "FAILED";
  const updated: PrintJobRecord = {
    ...queued,
    status,
    updatedAtIso: new Date().toISOString(),
    adapterDetail: result.detail,
    hardwareClaim: result.hardwareClaim,
  };
  store.jobs.set(jobId, updated);
  if (autoIntentKey && status === "SPOOLED") {
    store.autoPrintedIntents.add(autoIntentKey);
  }
  return updated;
}

/** Explicit reprint from persisted snapshot — never mutates checkout/finance. */
export async function reprintJob(
  store: PrintJobStore,
  originalJobId: string,
  scenario: SimulatedPrintScenario = "success",
): Promise<PrintJobRecord> {
  const original = store.jobs.get(originalJobId);
  if (!original) {
    throw new Error("print_job_not_found");
  }
  const reprintSnapshot: ThermalReceiptInput = {
    ...original.snapshot,
    reprintOfJobId: original.jobId,
    copyIndex: (original.snapshot.copyIndex ?? 1) + 1,
  };
  return submitPrintJob({
    store,
    snapshot: reprintSnapshot,
    invoiceId: original.invoiceId,
    workstationId: original.workstationId,
    kind: "REPRINT",
    parentJobId: original.jobId,
    scenario,
  });
}

/** Batch: one independent receipt job per patient invoice snapshot. */
export async function submitBatchPrintJobs(
  store: PrintJobStore,
  items: Array<{
    snapshot: ThermalReceiptInput;
    invoiceId: string;
    workstationId: string;
  }>,
  scenario: SimulatedPrintScenario = "success",
): Promise<{ batchId: string; jobs: PrintJobRecord[] }> {
  const batchId = `batch-${crypto.randomUUID?.() ?? Date.now()}`;
  const jobs: PrintJobRecord[] = [];
  for (const item of items) {
    const job = await submitPrintJob({
      store,
      snapshot: item.snapshot,
      invoiceId: item.invoiceId,
      workstationId: item.workstationId,
      kind: "BATCH_ITEM",
      batchId,
      scenario,
    });
    jobs.push(job);
  }
  return { batchId, jobs };
}

/** Recover UNKNOWN/FAILED with explicit user action — still no finance mutation. */
export async function recoverPrintJob(
  store: PrintJobStore,
  jobId: string,
  action: "retry" | "cancel",
  scenario: SimulatedPrintScenario = "success",
): Promise<PrintJobRecord> {
  const existing = store.jobs.get(jobId);
  if (!existing) throw new Error("print_job_not_found");
  if (action === "cancel") {
    const cancelled: PrintJobRecord = {
      ...existing,
      status: "CANCELLED",
      updatedAtIso: new Date().toISOString(),
      adapterDetail: "چاپ لغو شد توسط کاربر — وضعیت مالی بدون تغییر",
    };
    store.jobs.set(jobId, cancelled);
    return cancelled;
  }
  if (existing.status !== "FAILED" && existing.status !== "UNKNOWN") {
    throw new Error("print_job_not_recoverable");
  }
  const retried = await submitPrintJob({
    store,
    snapshot: existing.snapshot,
    invoiceId: existing.invoiceId,
    workstationId: existing.workstationId,
    kind: existing.kind === "TEST" ? "TEST" : "REPRINT",
    parentJobId: existing.jobId,
    scenario,
  });
  return { ...retried, attempt: existing.attempt + 1 };
}

export function jobsForInvoice(store: PrintJobStore, invoiceId: string): PrintJobRecord[] {
  return [...store.jobs.values()]
    .filter((j) => j.invoiceId === invoiceId)
    .sort((a, b) => a.createdAtIso.localeCompare(b.createdAtIso));
}
