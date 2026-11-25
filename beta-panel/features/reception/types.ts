import type { Requirement } from "@/lib/resources";

export type Patient = {
  patient_profile_id: string;
  person_id: string;
  first_name: string;
  last_name: string;
  birth_date: string | null;
};

export type Service = {
  id: string;
  service_name: string;
  default_duration_minutes: number;
  is_active: boolean;
};

export type RequirementsState =
  | { status: "idle" }
  | { status: "loading"; serviceId: string }
  | { status: "ready"; serviceId: string; items: Requirement[] }
  | { status: "error"; serviceId: string; message: string };
