export type StaffAccount = { account_id: string; is_active: boolean; login_identifier: string | null };

export type StaffRow = {
  staff_profile_id: string;
  person_id: string;
  first_name: string;
  last_name: string;
  staff_kind: string;
  medical_council_code: string | null;
  is_active: boolean;
  aggregate_version: number;
  created_at_utc: string;
  account: StaffAccount | null;
};

export const STAFF_KIND_LABEL: Record<string, string> = {
  DOCTOR: "پزشک",
  SPECIALIST: "متخصص",
  RECEPTIONIST: "پذیرش",
  NURSE: "پرستار",
  TECHNICIAN: "تکنسین",
  OTHER: "سایر",
};

export const STAFF_KINDS = Object.keys(STAFF_KIND_LABEL);

export const STAFF_PAGE_SIZE = 25;

export const MIN_PASSWORD_LENGTH = 12;

export function staffKindLabel(kind: string): string {
  return STAFF_KIND_LABEL[kind] ?? kind;
}
