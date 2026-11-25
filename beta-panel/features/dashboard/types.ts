export type PeriodSummary = { total: number; by_status: Record<string, number> };

export type Summary = {
  appointments: PeriodSummary | null;
  tomorrow_appointments?: PeriodSummary | null;
  patients_active: number | null;
  staff_active: number | null;
  services_active: number | null;
  resources_active: number | null;
};

export const UPCOMING_LIMIT = 8;

export type MetricCardDef = {
  key: string;
  label: string;
  value: number | null | undefined;
  href: string;
  icon: "calendar" | "patients" | "staff" | "catalog" | "layers" | "desk" | "alert";
  testId: string;
  hint?: string;
};
