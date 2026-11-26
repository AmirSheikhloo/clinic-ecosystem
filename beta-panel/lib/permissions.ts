import type { IconName } from "@/components/ui/icon-paths";

/** Permission codes mirror src/clinic_ecosystem/domain/access/permissions.py. */

export const P = {
  catalogServicesRead: "CATALOG_SERVICES_READ",
  allowManualOverbooking: "ALLOW_MANUAL_OVERBOOKING",
  patientsRegister: "BETA01B_PATIENTS_REGISTER",
  patientsSearch: "BETA01B_PATIENTS_SEARCH",
  resourcesRead: "BETA01B_CATALOG_RESOURCES_READ",
  appointmentsSchedule: "BETA01B_APPOINTMENTS_SCHEDULE_MANUAL",
  appointmentsList: "BETA01B_APPOINTMENTS_LIST",
  patientsViewProfile: "BETA02_PATIENTS_VIEW_PROFILE",
  patientsUpdate: "BETA02_PATIENTS_UPDATE",
  patientsSetActive: "BETA02_PATIENTS_SET_ACTIVE",
  patientsViewHistory: "BETA02_PATIENTS_VIEW_HISTORY",
  staffView: "BETA02_STAFF_VIEW",
  staffManage: "BETA02_STAFF_MANAGE",
  staffProvisionLogin: "BETA02_STAFF_PROVISION_LOGIN",
  accountsView: "BETA02_ACCOUNTS_VIEW",
  accountsSetActive: "BETA02_ACCOUNTS_SET_ACTIVE",
  rolesView: "BETA02_ROLES_VIEW",
  rolesManage: "BETA02_ROLES_MANAGE",
  userRolesAssign: "BETA02_USER_ROLES_ASSIGN",
  governanceView: "BETA02_GOVERNANCE_VIEW",
  governanceManage: "BETA02_GOVERNANCE_MANAGE",
  servicesManage: "BETA02_CATALOG_SERVICES_MANAGE",
  resourcesManage: "BETA02_CATALOG_RESOURCES_MANAGE",
  appointmentsDetails: "BETA02_APPOINTMENTS_VIEW_DETAILS",
  appointmentsCancel: "BETA02_APPOINTMENTS_CANCEL",
  appointmentsReschedule: "BETA02_APPOINTMENTS_RESCHEDULE",
  appointmentsCheckIn: "BETA02_APPOINTMENTS_CHECK_IN",
  appointmentsComplete: "BETA02_APPOINTMENTS_COMPLETE",
  appointmentsMarkNoShow: "BETA02_APPOINTMENTS_MARK_NO_SHOW",
  auditView: "BETA02_AUDIT_VIEW",
} as const;

export type NavGroupId = "work" | "clinic" | "admin" | "personal";

export type NavItem = {
  href: string;
  label: string;
  icon: IconName;
  group: NavGroupId;
  /** Visible when the user holds at least one of these; empty means always visible. */
  anyOf: readonly string[];
};

export const NAV_GROUPS: readonly { id: NavGroupId; label: string }[] = [
  { id: "work", label: "کار روزانه" },
  { id: "clinic", label: "کلینیک" },
  { id: "admin", label: "مدیریت" },
  { id: "personal", label: "شخصی" },
];

/** UI visibility only; the server remains the sole authority for every action. */
export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/dashboard", label: "داشبورد", icon: "dashboard", group: "work", anyOf: [] },
  { href: "/desk", label: "میز پذیرش", icon: "desk", group: "work", anyOf: [P.appointmentsSchedule, P.patientsSearch] },
  { href: "/appointments", label: "مدیریت نوبت‌ها", icon: "calendar", group: "work", anyOf: [P.appointmentsList] },
  { href: "/patients", label: "بیماران", icon: "patients", group: "clinic", anyOf: [P.patientsSearch, P.patientsRegister] },
  { href: "/catalog", label: "خدمات و منابع", icon: "catalog", group: "clinic", anyOf: [P.catalogServicesRead, P.resourcesRead, P.servicesManage, P.resourcesManage] },
  { href: "/staff", label: "کارکنان", icon: "staff", group: "admin", anyOf: [P.staffView] },
  { href: "/access", label: "کاربران و دسترسی", icon: "access", group: "admin", anyOf: [P.accountsView, P.rolesView, P.governanceView] },
  { href: "/audit", label: "حسابرسی", icon: "list", group: "admin", anyOf: [P.auditView] },
  { href: "/preferences", label: "ظاهر و ترجیحات", icon: "palette", group: "personal", anyOf: [] },
];

export function hasAny(granted: ReadonlySet<string>, codes: readonly string[]): boolean {
  return codes.length === 0 || codes.some((code) => granted.has(code));
}

export function visibleNav(granted: ReadonlySet<string>): NavItem[] {
  return NAV_ITEMS.filter((item) => hasAny(granted, item.anyOf));
}

/** Longest-prefix match so /catalog/manage does not shadow /catalog. */
export function activeNav(pathname: string, items: readonly NavItem[] = NAV_ITEMS): NavItem | undefined {
  return items
    .filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0];
}
