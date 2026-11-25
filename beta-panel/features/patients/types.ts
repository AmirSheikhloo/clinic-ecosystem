export type PatientRow = {
  patient_profile_id: string;
  person_id: string;
  first_name: string;
  last_name: string;
  birth_date: string | null;
  dossier_number: string | null;
  is_active: boolean;
  aggregate_version: number;
  created_at_utc: string;
};

export type PatientHistoryItem = {
  appointment_id: string;
  status: string;
  booking_channel: string;
  scheduled_start_at_utc: string;
  scheduled_end_at_utc: string;
  service_id: string;
  service_name: string;
};

export type PatientStatusFilter = "active" | "inactive" | "all";

export const PATIENT_PAGE_SIZE = 20;
