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

const OPERATIONAL: readonly QuickAction[] = [
  { href: "/desk", label: "نوبت‌دهی جدید", hint: "میز پذیرش", icon: "desk", allowed: (can) => can(P.appointmentsSchedule) },
  { href: "/patients", label: "جستجوی بیمار", hint: "فهرست بیماران", icon: "patients", allowed: (can) => can(P.patientsSearch) },
  {
    href: "/patients?register=1",
    label: "ثبت بیمار",
    hint: "ثبت هویت اولیه",
    icon: "plus",
    allowed: (can) => can(P.patientsRegister),
  },
  { href: "/appointments", label: "مدیریت نوبت‌ها", hint: "فهرست، روز، هفته و ماه", icon: "calendar", allowed: (can) => can(P.appointmentsList) },
];

const MANAGEMENT: readonly QuickAction[] = [
  { href: "/appointments", label: "مدیریت نوبت‌ها", hint: "فهرست و تقویم عملیاتی", icon: "calendar", allowed: (can) => can(P.appointmentsList) },
  { href: "/staff", label: "کارکنان", hint: "پروفایل و حساب ورود", icon: "staff", allowed: (can) => can(P.staffView) },
  { href: "/access", label: "کاربران و دسترسی", hint: "نقش‌ها و مجوزها", icon: "access", allowed: (can) => can(P.accountsView) || can(P.rolesView) },
  { href: "/catalog/manage", label: "مدیریت خدمات", hint: "تعرفه و الزامات", icon: "catalog", allowed: (can) => can(P.servicesManage) || can(P.resourcesManage) },
  { href: "/desk", label: "میز پذیرش", hint: "ثبت نوبت دستی", icon: "desk", allowed: (can) => can(P.appointmentsSchedule) },
];

const SUPERVISION: readonly QuickAction[] = [
  { href: "/staff", label: "نظارت کارکنان", hint: "فقط در محدودهٔ مجوز شما", icon: "staff", allowed: (can) => can(P.staffView) },
  { href: "/access", label: "حساب‌های کاربری", hint: "وضعیت ورود همکاران", icon: "access", allowed: (can) => can(P.accountsView) },
];

export function quickActionsFor(audience: DashboardAudience): readonly QuickAction[] {
  if (audience.composition === "management") return MANAGEMENT;
  if (audience.headReception) return [...OPERATIONAL, ...SUPERVISION];
  return OPERATIONAL;
}
