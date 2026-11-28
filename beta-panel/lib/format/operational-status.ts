/** Reception-facing operational presentation — maps domain status → PO-approved labels. */

export type OpsPresentation =
  | "waiting"
  | "completed"
  | "needs_status"
  | "cancelled"
  | "not_performed";

export type OpsTone = "waiting" | "completed" | "needs" | "cancelled" | "not_performed";

const LABEL: Record<OpsPresentation, string> = {
  waiting: "در انتظار",
  completed: "انجام‌شده",
  needs_status: "نیازمند تعیین وضعیت",
  cancelled: "لغوشده",
  not_performed: "انجام‌نشده",
};

/**
 * Presentation mapping preserves underlying domain facts.
 * CONFIRMED/SCHEDULED/IN_PROGRESS/CHECKED_IN before due → waiting or needs_status.
 * NO_SHOW → not_performed (distinct from cancellation).
 */
export function operationalPresentation(
  status: string,
  opts: { needsStatus?: boolean } = {},
): OpsPresentation {
  if (status === "CANCELLED") return "cancelled";
  if (status === "COMPLETED") return "completed";
  if (status === "NO_SHOW") return "not_performed";
  if (opts.needsStatus) return "needs_status";
  if (status === "CHECKED_IN") return "needs_status";
  return "waiting";
}

export function operationalStatusLabel(presentation: OpsPresentation): string {
  return LABEL[presentation];
}

export function operationalStatusTone(presentation: OpsPresentation): OpsTone {
  if (presentation === "needs_status") return "needs";
  return presentation;
}

export const METRIC_FILTER_LABELS: Record<string, string> = {
  today: "نوبت‌های امروز",
  upcoming: "نوبت‌های پیش رو",
  needs_status: "نیازمند تعیین وضعیت",
  cancelled: "نوبت‌های لغوشده",
  online: "رزروهای آنلاین",
};

export function financialStatusFa(code: string | null | undefined): string {
  if (!code) return "وضعیت مالی نامشخص";
  const map: Record<string, string> = {
    PAID: "پرداخت‌شده",
    UNPAID: "پرداخت‌نشده",
    PARTIAL: "پرداخت ناقص",
    ZERO_PAYABLE: "بدون مبلغ قابل پرداخت",
    FULL_REFUND: "عودت کامل",
    PARTIAL_REFUND: "عودت جزئی",
    UNKNOWN: "وضعیت مالی نامشخص",
    NONE: "وضعیت مالی نامشخص",
  };
  return map[code] ?? (code.match(/^[A-Z_]+$/) ? "وضعیت مالی نامشخص" : code);
}
