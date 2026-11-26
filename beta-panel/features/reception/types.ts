import type { Requirement } from "@/lib/resources";

export type Patient = {
  is_active?: boolean;
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
  default_price_irr: number;
  is_active: boolean;
};

/** One draft service row on the reception desk (independent appointment identity on submit). */
export type DraftServiceLine = {
  key: string;
  serviceId: string;
  serviceName: string;
  resourceIds: string[];
  resourceNames: string[];
  localStart: string;
  durationMinutes: number;
  priceIrr: number;
};

export type RequirementsState =
  | { status: "idle" }
  | { status: "loading"; serviceId: string }
  | { status: "ready"; serviceId: string; items: Requirement[] }
  | { status: "error"; serviceId: string; message: string };
