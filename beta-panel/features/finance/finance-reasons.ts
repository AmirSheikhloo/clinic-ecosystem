/** Operation-specific predefined reason catalogs (FIN-04). "OTHER" requires free-text explanation. */

export type ReasonOption = {
  code: string;
  labelFa: string;
  requiresExplanation?: boolean;
};

export const DISCOUNT_REASONS: ReasonOption[] = [
  { code: "STAFF_COURTESY", labelFa: "تخفیف پرسنلی / حسن نیت" },
  { code: "PACKAGE_ADJUST", labelFa: "تعدیل بسته خدماتی" },
  { code: "PRICING_ERROR", labelFa: "اصلاح خطای قیمت‌گذاری" },
  { code: "OTHER", labelFa: "سایر", requiresExplanation: true },
];

export const ADJUSTMENT_REASONS: ReasonOption[] = [
  { code: "POST_PAYMENT_CORRECTION", labelFa: "اصلاح پس از پرداخت" },
  { code: "LINE_MISCHARGE", labelFa: "اشتباه در ثبت ردیف خدمت" },
  { code: "MANAGER_APPROVED", labelFa: "تصویب مدیر پذیرش" },
  { code: "OTHER", labelFa: "سایر", requiresExplanation: true },
];

export const REFUND_REASONS: ReasonOption[] = [
  { code: "SERVICE_NOT_RENDERED", labelFa: "خدمت ارائه نشد" },
  { code: "DUPLICATE_PAYMENT", labelFa: "پرداخت تکراری" },
  { code: "PATIENT_WITHDRAWAL", labelFa: "انصراف بیمار" },
  { code: "OTHER", labelFa: "سایر", requiresExplanation: true },
];

export const CANCEL_REASONS: ReasonOption[] = [
  { code: "PATIENT_REQUEST", labelFa: "درخواست بیمار" },
  { code: "CLINIC_CLOSURE", labelFa: "تعطیلی / محدودیت کلینیک" },
  { code: "PROVIDER_UNAVAILABLE", labelFa: "عدم حضور ارائه‌دهنده" },
  { code: "SCHEDULING_ERROR", labelFa: "خطای زمان‌بندی" },
  { code: "OTHER", labelFa: "سایر", requiresExplanation: true },
];

/** Soft approval threshold (IRR) for money-out ops — UI confirmation gate only. */
export const MONEY_OUT_APPROVAL_THRESHOLD_IRR = 5_000_000;

export function reasonRequiresExplanation(options: ReasonOption[], code: string): boolean {
  return !!options.find((o) => o.code === code)?.requiresExplanation;
}
