export type Summary = {
  appointments: { total: number; by_status: Record<string, number> } | null;
  patients_active: number | null;
  staff_active: number | null;
  services_active: number | null;
  resources_active: number | null;
};

export const UPCOMING_LIMIT = 8;
