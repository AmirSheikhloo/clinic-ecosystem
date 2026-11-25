export type AppointmentItem = {
  appointment_id: string;
  patient_first_name: string;
  patient_last_name: string;
  service_name: string;
  status: string;
  scheduled_start_at_utc: string;
  scheduled_end_at_utc: string;
};

export type CalendarItem = AppointmentItem & {
  patient_profile_id: string;
  service_id: string;
  booking_channel: string;
  capacity_pool: string;
  resource_names: string[];
  aggregate_version: number;
};

export type CalendarResponse = { items: CalendarItem[]; truncated: boolean; limit: number };

export type AppointmentDetails = CalendarItem & {
  created_at_utc: string;
  updated_at_utc: string;
  allocations: Array<{
    resource_id: string;
    resource_name: string;
    resource_type: string;
    allocation_status: string;
  }>;
  can_cancel: boolean;
  can_reschedule: boolean;
};

export type SortKey = "time" | "patient" | "service";

export const CALENDAR_STATUSES = [
  "CONFIRMED",
  "CHECKED_IN",
  "COMPLETED",
  "CANCELLED",
  "NO_SHOW",
  "PENDING_PAYMENT_HOLD",
  "EXPIRED_HOLD",
] as const;

export const CALENDAR_LIMIT = 500;
