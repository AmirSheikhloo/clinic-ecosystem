/** Compact 80mm (default) / 58mm thermal receipt text builder — synthetic preview. */

export type ThermalWidth = 58 | 80;

export type ThermalLine = {
  description: string;
  amountIrr: number;
};

export type ThermalReceiptInput = {
  clinicName: string;
  invoiceNumber: string;
  jalaliDate: string;
  patientDisplay: string;
  lines: ThermalLine[];
  discountIrr?: number;
  totalPayableIrr: number;
  paidIrr?: number;
  methodLabel?: string;
  nextHint?: string;
  synthetic?: boolean;
  widthMm?: ThermalWidth;
};

function money(n: number): string {
  return new Intl.NumberFormat("en-US").format(Math.trunc(n));
}

/** Build monospace RTL-friendly plain text for thermal preview / simulated adapter. */
export function buildThermalReceiptText(input: ThermalReceiptInput): string {
  const width = input.widthMm === 58 ? 32 : 42;
  const rule = "-".repeat(width);
  const lines = [
    input.clinicName,
    rule,
    `شماره: ${input.invoiceNumber}`,
    `تاریخ: ${input.jalaliDate}`,
    `بیمار: ${input.patientDisplay}`,
    rule,
    ...input.lines.map((l) => `${l.description}  ${money(l.amountIrr)}`),
  ];
  if (input.discountIrr) lines.push(`تخفیف: ${money(input.discountIrr)}`);
  lines.push(rule);
  lines.push(`مبلغ قابل پرداخت: ${money(input.totalPayableIrr)} ریال`);
  if (input.paidIrr != null) lines.push(`پرداخت‌شده: ${money(input.paidIrr)} · ${input.methodLabel || ""}`);
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

export type PrintAdapterResult = {
  ok: boolean;
  jobId: string;
  mode: "simulated" | "browser_fallback";
  detail: string;
};

/** Simulated workstation print adapter — never claims physical hardware success. */
export async function simulatedThermalPrint(text: string): Promise<PrintAdapterResult> {
  const jobId = `sim-${Date.now()}`;
  if (typeof window !== "undefined") {
    // Expose for Playwright assertions without opening a real printer dialog.
    (window as unknown as { __clinicLastPrint?: string }).__clinicLastPrint = text;
  }
  return {
    ok: true,
    jobId,
    mode: "simulated",
    detail: "چاپ شبیه‌سازی‌شده — سخت‌افزار واقعی متصل نیست",
  };
}
