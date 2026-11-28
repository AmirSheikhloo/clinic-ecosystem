export type PeriodSummary = {
  total: number;
  by_status: Record<string, number>;
  unique_patients?: number;
  waiting_checked_in?: number;
  upcoming_count?: number;
  needs_status_count?: number;
  cancelled_count?: number;
  online_bookings_today?: number;
  online_unreviewed_count?: number;
};

/** Enriched dashboard/day row fields (optional when data/permission present). */
export type DayEnrichment = {
  national_id_masked?: string | null;
  patient_phone_masked?: string | null;
  insurance_label?: string | null;
  practitioner_name?: string | null;
  practitioner_names?: string[] | null;
  financial_status_code?: string | null;
  financial_status_label?: string | null;
  outstanding_irr?: number | null;
  payment_method_label?: string | null;
  finance_review_required?: boolean;
  booking_channel?: string | null;
  created_at_utc?: string | null;
  online_reviewed?: boolean;
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
export const DAY_PAGE_SIZES = [5, 10, 15, 20, 40, 50] as const;
export const DAY_PAGE_DEFAULT: (typeof DAY_PAGE_SIZES)[number] = 10;

export type MetricAccent = "today" | "upcoming" | "needs" | "cancelled" | "online";

export type MetricCardDef = {
  key: string;
  label: string;
  value: number | null | undefined;
  href: string;
  icon: import("@/components/ui/icon-paths").IconName;
  testId: string;
  hint?: string;
  accent?: MetricAccent;
  /** When false, card is display-only (Today's Appointments). */
  interactive?: boolean;
  /** Red review badge count (online unreviewed). */
  badge?: number;
  filterKey?: string;
};
