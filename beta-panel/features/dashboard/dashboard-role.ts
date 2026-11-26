import { P } from "@/lib/permissions";

export type DashboardComposition = "operational" | "management";

export type DashboardAudience = {
  composition: DashboardComposition;
  /** Operational dashboard with extra supervision shortcuts (no separate product surface). */
  headReception: boolean;
  label: string;
};

const MANAGEMENT_GOVERNANCE = new Set(["CLINIC_OWNER", "CLINIC_MANAGER"]);

/**
 * Chooses dashboard composition from governance + permissions.
 * Head receptionist is approximated as RECEPTIONIST (or no owner/manager) with at least one
 * supervision permission — there is no separate HEAD_RECEPTIONIST governance code yet (see ACR).
 */
export function resolveDashboardAudience(
  governance: readonly string[],
  can: (code: string) => boolean,
): DashboardAudience {
  const gov = new Set(governance);
  const isOwnerOrManager = [...MANAGEMENT_GOVERNANCE].some((role) => gov.has(role));
  const isDeputy = gov.has("DEPUTY_ADMIN");
  const supervision =
    can(P.staffView) || can(P.accountsView) || can(P.rolesView) || can(P.governanceView) || can(P.servicesManage);

  if (isOwnerOrManager || (isDeputy && supervision && !can(P.appointmentsSchedule))) {
    return {
      composition: "management",
      headReception: false,
      label: isOwnerOrManager ? (gov.has("CLINIC_OWNER") ? "مالک کلینیک" : "مدیر کلینیک") : "معاون مدیر",
    };
  }

  const operationalOps = can(P.appointmentsList) || can(P.appointmentsSchedule) || can(P.patientsSearch);
  const headReception = !isOwnerOrManager && supervision && operationalOps;

  if (isDeputy && supervision) {
    return { composition: "management", headReception: false, label: "معاون مدیر" };
  }

  const receptionLabel = headReception
    ? "سرپرست پذیرش"
    : gov.has("RECEPTIONIST") || can(P.appointmentsSchedule)
      ? "پذیرش"
      : "کاربر عملیاتی";
  return {
    composition: "operational",
    headReception,
    label: receptionLabel,
  };
}
