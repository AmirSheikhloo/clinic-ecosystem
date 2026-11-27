export type PeriodSummary = {
  total: number;
  by_status: Record<string, number>;
  unique_patients?: number;
  waiting_checked_in?: number;
  upcoming_count?: number;
  needs_status_count?: number;
  cancelled_count?: number;
};

export type FinanceSummary = {
  posted_invoices: number;
  draft_invoices: number;
  receipt_count: number;
  receipt_total_irr: number;
  refund_count: number;
  refund_total_irr: number;
  net_collected_irr: number;
};

export type Summary = {
  appointments: PeriodSummary | null;
  tomorrow_appointments?: PeriodSummary | null;
  waiting_room?: { checked_in_count: number } | null;
  future_waitlist?: { open_count: number } | null;
  finance?: FinanceSummary | null;
  patients_active: number | null;
  staff_active: number | null;
  services_active: number | null;
  resources_active: number | null;
};

export const UPCOMING_LIMIT = 12;
export const DAY_PAGE_SIZES = [25, 50, 100] as const;

export type MetricCardDef = {
  key: string;
  label: string;
  value: number | null | undefined;
  href: string;
  icon: "calendar" | "patients" | "staff" | "catalog" | "layers" | "desk" | "alert" | "list";
  testId: string;
  hint?: string;
  accent?: "blue" | "purple" | "amber" | "rose" | "green";
  filterKey?: string;
};
