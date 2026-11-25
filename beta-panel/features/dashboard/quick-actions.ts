import type { IconName } from "@/components/ui/icon-paths";
import { P } from "@/lib/permissions";

export type QuickAction = { href: string; label: string; hint: string; icon: IconName; allowed: (can: (code: string) => boolean) => boolean };

export const QUICK_ACTIONS: readonly QuickAction[] = [
  { href: "/desk", label: "نوبت‌دهی جدید", hint: "میز پذیرش", icon: "desk", allowed: (can) => can(P.appointmentsSchedule) },
  { href: "/patients", label: "ثبت و جستجوی بیمار", hint: "فهرست بیماران", icon: "patients", allowed: (can) => can(P.patientsSearch) || can(P.patientsRegister) },
  { href: "/appointments", label: "تقویم نوبت‌ها", hint: "نمای روز، هفته و ماه", icon: "calendar", allowed: (can) => can(P.appointmentsList) },
  { href: "/catalog", label: "خدمات و منابع", hint: "تعرفه و الزامات", icon: "catalog", allowed: (can) => can(P.catalogServicesRead) },
];
