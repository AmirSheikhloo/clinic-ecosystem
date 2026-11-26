export type AuditEntry = {
  id: string;
  actor_type: string;
  actor_id: string | null;
  actor_login: string | null;
  operation: string;
  target_type: string;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at_utc: string;
};

export const AUDIT_PAGE_SIZE = 25;

const OPERATION_LABELS: Record<string, string> = {
  "patient.registered": "ثبت بیمار",
  "patient.updated": "ویرایش بیمار",
  "patient.activated": "فعال‌سازی بیمار",
  "patient.deactivated": "غیرفعال‌سازی بیمار",
  "appointment.checked_in": "ثبت حضور",
  "appointment.rescheduled": "جابه‌جایی نوبت",
  "appointment.cancelled": "لغو نوبت",
  "appointment.completed": "اتمام نوبت",
  "appointment.no_show": "ثبت عدم حضور",
  "appointment.demo_confirmed": "نوبت نمونه — تأییدشده",
  "appointment.demo_checked_in": "نوبت نمونه — حضور",
  "appointment.demo_completed": "نوبت نمونه — اتمام",
  "appointment.demo_cancelled": "نوبت نمونه — لغو",
  "appointment.demo_no_show": "نوبت نمونه — عدم حضور",
  ALLOW_MANUAL_OVERBOOKING: "تأیید هم‌پوشانی دستی",
  "staff.created": "ثبت کارمند",
  "staff.updated": "ویرایش کارمند",
  "staff.activated": "فعال‌سازی کارمند",
  "staff.deactivated": "غیرفعال‌سازی کارمند",
  "account.provisioned": "ایجاد حساب ورود",
  "demo.seed_marker": "نشانگر دادهٔ نمونه",
};

const TARGET_LABELS: Record<string, string> = {
  appointment: "نوبت",
  patient: "بیمار",
  patient_profile: "بیمار",
  staff: "کارمند",
  account: "حساب",
  service: "خدمت",
  resource: "منبع",
  role: "نقش",
  demo_dataset: "دادهٔ نمونه",
};

export function operationLabel(code: string): string {
  return OPERATION_LABELS[code] ?? code;
}

export function targetTypeLabel(code: string): string {
  return TARGET_LABELS[code] ?? code;
}
