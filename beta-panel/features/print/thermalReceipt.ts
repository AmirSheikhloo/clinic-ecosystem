/** Compact 80mm (default) / 58mm thermal receipt text builder — synthetic preview. */

export type ThermalWidth = 58 | 80;

export type ThermalLine = {
  description: string;
  amountIrr: number;
  quantity?: number;
};

export type ThermalReceiptInput = {
  clinicName: string;
  invoiceNumber: string;
  /** Immutable snapshot timestamp (ISO or Jalali label); never live tariff. */
  jalaliDate: string;
  patientDisplay: string;
  lines: ThermalLine[];
  discountIrr?: number;
  totalPayableIrr: number;
  paidIrr?: number;
  methodLabel?: string;
  financialStatus?: string;
  /** Course session e.g. "جلسه 4 از 10" — clinical ordinal, not a booking. */
  courseSessionHint?: string;
  /** Suggested next visit; must not imply a confirmed appointment. */
  nextHint?: string;
  synthetic?: boolean;
  widthMm?: ThermalWidth;
  /** Reprint copy marker — never mutates finance. */
  reprintOfJobId?: string;
  copyIndex?: number;
};

function money(n: number): string {
  return new Intl.NumberFormat("en-US").format(Math.trunc(n));
}

const FORBIDDEN_PATTERNS: RegExp[] = [
  /کد\s*ملی/i,
  /national[\s_-]?id/i,
  /\b\d{10}\b/, // raw 10-digit national id style
  /شماره\s*کارت/i,
  /cvv/i,
  /iban/i,
  /شبا/i,
];

/** Reject privacy-unsafe fields before building printable text. */
export function assertPrivacySafeReceiptFields(input: ThermalReceiptInput): void {
  const blob = [
    input.patientDisplay,
    input.nextHint ?? "",
    input.courseSessionHint ?? "",
    ...input.lines.map((l) => l.description),
  ].join("\n");
  for (const re of FORBIDDEN_PATTERNS) {
    if (re.test(blob) || re.test(input.clinicName)) {
      throw new Error(`privacy_blocked:${re.source}`);
    }
  }
}

/** Build monospace RTL-friendly plain text for thermal preview / simulated adapter. */
export function buildThermalReceiptText(input: ThermalReceiptInput): string {
  assertPrivacySafeReceiptFields(input);
  const width = input.widthMm === 58 ? 32 : 42;
  const rule = "-".repeat(width);
  const lines = [
    input.clinicName,
    rule,
    `شماره: ${input.invoiceNumber}`,
    `تاریخ: ${input.jalaliDate}`,
    `بیمار: ${input.patientDisplay}`,
  ];
  if (input.courseSessionHint) {
    lines.push(`دوره: ${input.courseSessionHint}`);
  }
  if (input.reprintOfJobId) {
    lines.push(`نسخه چاپ مجدد · ${input.copyIndex ?? 2}`);
  }
  lines.push(rule);
  for (const l of input.lines) {
    const qty = l.quantity && l.quantity !== 1 ? `×${l.quantity} ` : "";
    lines.push(`${qty}${l.description}  ${money(l.amountIrr)}`);
  }
  if (input.discountIrr) lines.push(`تخفیف: ${money(input.discountIrr)}`);
  lines.push(rule);
  lines.push(`مبلغ قابل پرداخت: ${money(input.totalPayableIrr)} ریال`);
  if (input.paidIrr != null) {
    lines.push(`پرداخت‌شده: ${money(input.paidIrr)} · ${input.methodLabel || ""}`.trimEnd());
  }
  if (input.financialStatus) {
    lines.push(`وضعیت: ${input.financialStatus}`);
  }
  if (input.nextHint) {
    lines.push(rule);
    lines.push(input.nextHint);
    lines.push("(پیشنهاد — نوبت قطعی نیست)");
  }
  if (input.synthetic !== false) {
    lines.push(rule);
    lines.push("*** نمونه مصنوعی — فاکتور مالیاتی نیست ***");
  }
  return lines.join("\n");
}

export type PrintAdapterMode = "simulated" | "browser_fallback" | "qz_blocked";

export type PrintAdapterResult = {
  ok: boolean;
  jobId: string;
  mode: PrintAdapterMode;
  /** Never claim physical hardware success from the simulated path. */
  hardwareClaim: "none" | "browser_dialog" | "blocked_pending_approval";
  status: "SPOOLED_SIMULATED" | "FAILED" | "UNKNOWN" | "BLOCKED";
  detail: string;
};

export type SimulatedPrintScenario =
  | "success"
  | "failed"
  | "unknown"
  | "disconnected"
  | "duplicate_ignored";

/**
 * Simulated workstation print adapter — never claims physical hardware success.
 * Real QZ signing / silent print remains BLOCKED without external approvals.
 */
export async function simulatedThermalPrint(
  text: string,
  opts?: {
    jobId?: string;
    scenario?: SimulatedPrintScenario;
    alreadyPrintedJobIds?: ReadonlySet<string>;
  },
): Promise<PrintAdapterResult> {
  const jobId = opts?.jobId ?? `sim-${crypto.randomUUID?.() ?? Date.now()}`;
  const scenario = opts?.scenario ?? "success";

  if (typeof window !== "undefined") {
    (window as unknown as { __clinicLastPrint?: string }).__clinicLastPrint = text;
  }

  if (opts?.alreadyPrintedJobIds?.has(jobId)) {
    return {
      ok: false,
      jobId,
      mode: "simulated",
      hardwareClaim: "none",
      status: "FAILED",
      detail: "تکرار خودکار چاپ رد شد — برای نسخه جدید از چاپ مجدد صریح استفاده کنید",
    };
  }

  if (scenario === "disconnected") {
    return {
      ok: false,
      jobId,
      mode: "simulated",
      hardwareClaim: "none",
      status: "FAILED",
      detail: "چاپگر قطع است — سخت‌افزار واقعی متصل نیست",
    };
  }
  if (scenario === "failed") {
    return {
      ok: false,
      jobId,
      mode: "simulated",
      hardwareClaim: "none",
      status: "FAILED",
      detail: "خطای شبیه‌سازی‌شده چاپ (کاغذ/اسپول)",
    };
  }
  if (scenario === "unknown") {
    return {
      ok: false,
      jobId,
      mode: "simulated",
      hardwareClaim: "none",
      status: "UNKNOWN",
      detail: "وضعیت فیزیکی نامشخص پس از پذیرش در صف — چاپ مجدد صریح مجاز است، پرداخت تکرار نمی‌شود",
    };
  }

  return {
    ok: true,
    jobId,
    mode: "simulated",
    hardwareClaim: "none",
    status: "SPOOLED_SIMULATED",
    detail: "چاپ شبیه‌سازی‌شده — سخت‌افزار واقعی متصل نیست؛ موفقیت سخت‌افزاری ادعا نشده",
  };
}

/** Explicit disclosure: browser print cannot guarantee silent/unattended output. */
export function browserPrintFallbackDisclosure(): PrintAdapterResult {
  return {
    ok: false,
    jobId: `browser-${Date.now()}`,
    mode: "browser_fallback",
    hardwareClaim: "browser_dialog",
    status: "BLOCKED",
    detail:
      "چاپ مرورگر نیاز به تأیید کاربر دارد و چاپ بی‌صدا را تضمین نمی‌کند. پل QZ تأییدنشده است.",
  };
}

/** Real QZ path remains gated — private key must never ship in the frontend. */
export function qzHardwarePathBlocked(): PrintAdapterResult {
  return {
    ok: false,
    jobId: `qz-blocked-${Date.now()}`,
    mode: "qz_blocked",
    hardwareClaim: "blocked_pending_approval",
    status: "BLOCKED",
    detail:
      "امضای QZ، دسترسی سخت‌افزار و چاپ بدون مراقبت پشت تأیید امنیتی خارجی است — فقط شبیه‌سازی فعال است",
  };
}
