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

export type StatusTone = "neutral" | "ok" | "warn" | "danger" | "info";

const STATUS_TONE: Record<string, StatusTone> = {
  SCHEDULED: "info",
  CONFIRMED: "ok",
  CHECKED_IN: "ok",
  IN_PROGRESS: "info",
  COMPLETED: "neutral",
  CANCELLED: "danger",
  NO_SHOW: "warn",
  HELD: "warn",
  PENDING_PAYMENT_HOLD: "warn",
  EXPIRED_HOLD: "neutral",
};

export function appointmentStatusTone(status: string): StatusTone {
  return STATUS_TONE[status] ?? "neutral";
}

export function bookingChannelLabel(channel: string): string {
  return channel === "MANUAL" || channel === "MANUAL_STAFF" ? "ثبت دستی" : "آنلاین";
}

export function capacityPoolLabel(pool: string): string {
  return pool === "MANUAL" ? "ظرفیت دستی" : "ظرفیت آنلاین";
}
