import type { DraftServiceLine, Patient } from "./types";

/** One temporary cart slot — independent beneficiary, no shared family account required. */
export type CartPatientSlot = {
  key: string;
  patient: Patient;
  insuranceCode: string;
  lines: DraftServiceLine[];
};

export type MultiPatientSettlementResult = {
  patientId: string;
  patientName: string;
  ok: boolean;
  message: string;
  invoiceId?: string;
  invoiceNumber?: string | null;
  outstanding?: number;
};

export function createCartSlot(patient: Patient, insuranceCode = "NONE"): CartPatientSlot {
  return {
    key: `cart-${patient.patient_profile_id}-${Date.now()}`,
    patient,
    insuranceCode,
    lines: [],
  };
}

export function upsertPatientSlot(slots: CartPatientSlot[], patient: Patient, insuranceCode?: string): CartPatientSlot[] {
  const existing = slots.find((s) => s.patient.patient_profile_id === patient.patient_profile_id);
  if (existing) {
    return slots.map((s) =>
      s.patient.patient_profile_id === patient.patient_profile_id
        ? { ...s, patient, insuranceCode: insuranceCode ?? s.insuranceCode }
        : s,
    );
  }
  return [...slots, createCartSlot(patient, insuranceCode ?? "NONE")];
}

export function addLineToPatient(
  slots: CartPatientSlot[],
  patientId: string,
  line: DraftServiceLine,
): CartPatientSlot[] {
  return slots.map((s) =>
    s.patient.patient_profile_id === patientId
      ? { ...s, lines: [...s.lines, { ...line, key: `${line.key}-${s.lines.length}-${Date.now()}` }] }
      : s,
  );
}

export function removeLineFromPatient(
  slots: CartPatientSlot[],
  patientId: string,
  lineKey: string,
): CartPatientSlot[] {
  return slots.map((s) =>
    s.patient.patient_profile_id === patientId
      ? { ...s, lines: s.lines.filter((l) => l.key !== lineKey) }
      : s,
  );
}

export function removePatientSlot(slots: CartPatientSlot[], patientId: string): CartPatientSlot[] {
  return slots.filter((s) => s.patient.patient_profile_id !== patientId);
}
