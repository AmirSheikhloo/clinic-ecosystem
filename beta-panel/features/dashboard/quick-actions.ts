import type { IconName } from "@/components/ui/icon-paths";
import { P } from "@/lib/permissions";
import type { DashboardAudience } from "./dashboard-role";

export type QuickAction = {
  href: string;
  label: string;
  hint: string;
  icon: IconName;
  allowed: (can: (code: string) => boolean) => boolean;
};

/** Ordinary receptionist: exactly three equal action cards (Task 34 §8 / DASH-01). */
const OPERATIONAL: readonly QuickAction[] = [
  {
    href: "/desk",
    label: "نوبت‌دهی جدید",
    hint: "ثبت نوبت و پذیرش",
    icon: "desk",
    allowed: (can) => can(P.appointmentsSchedule),
  },
  {
    href: "/patients",
    label: "جستجوی بیمار",
    hint: "شناسایی و پرونده",
    icon: "patients",
    allowed: (can) => can(P.patientsSearch),
  },
  {
    href: "/appointments",
    label: "تقویم نوبت‌ها",
    hint: "روز، هفته و ماه",
    icon: "calendar",
    allowed: (can) => can(P.appointmentsList),
  },
];

const MANAGEMENT: readonly QuickAction[] = [
  { href: "/appointments", label: "مدیریت نوبت‌ها", hint: "فهرست و تقویم عملیاتی", icon: "calendar", allowed: (can) => can(P.appointmentsList) },
  { href: "/staff", label: "کارکنان", hint: "پروفایل و حساب ورود", icon: "staff", allowed: (can) => can(P.staffView) },
  { href: "/access", label: "کاربران و دسترسی", hint: "نقش‌ها و مجوزها", icon: "access", allowed: (can) => can(P.accountsView) || can(P.rolesView) },
  { href: "/catalog/manage", label: "مدیریت خدمات", hint: "تعرفه و الزامات", icon: "catalog", allowed: (can) => can(P.servicesManage) || can(P.resourcesManage) },
  { href: "/desk", label: "میز پذیرش", hint: "ثبت نوبت دستی", icon: "desk", allowed: (can) => can(P.appointmentsSchedule) },
];

export function quickActionsFor(audience: DashboardAudience): readonly QuickAction[] {
  if (audience.composition === "management") return MANAGEMENT;
  return OPERATIONAL;
}
