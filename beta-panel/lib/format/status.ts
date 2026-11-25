/** Persian labels for known appointment statuses — display only. */

const STATUS_FA: Record<string, string> = {
  SCHEDULED: "زمان‌بندی‌شده",
  CONFIRMED: "تأییدشده",
  CHECKED_IN: "حضور",
  IN_PROGRESS: "در حال انجام",
  COMPLETED: "انجام‌شده",
  CANCELLED: "لغوشده",
  NO_SHOW: "عدم حضور",
  HELD: "رزرو موقت",
  PENDING_PAYMENT_HOLD: "در انتظار پرداخت",
  EXPIRED_HOLD: "رزرو منقضی‌شده",
};

export function appointmentStatusLabel(status: string): string {
  return STATUS_FA[status] ?? status;
}
