import assert from "node:assert/strict";
import { test } from "node:test";
import {
  addLineToPatient,
  createCartSlot,
  removeLineFromPatient,
  removePatientSlot,
  upsertPatientSlot,
} from "./multi-patient-cart";
import type { DraftServiceLine, Patient } from "./types";

const patientA: Patient = {
  patient_profile_id: "p-a",
  person_id: "person-a",
  first_name: "آوا",
  last_name: "رضایی",
  birth_date: null,
};

const patientB: Patient = {
  patient_profile_id: "p-b",
  person_id: "person-b",
  first_name: "نیما",
  last_name: "کریمی",
  birth_date: null,
};

const line = (key: string): DraftServiceLine => ({
  key,
  serviceId: "svc-1",
  serviceName: "ویزیت",
  resourceIds: ["r1"],
  resourceNames: ["اتاق ۱"],
  localStart: "2026-11-27T10:00",
  durationMinutes: 30,
  priceIrr: 1_000_000,
});

test("multi-patient cart keeps independent per-patient lines", () => {
  let slots = upsertPatientSlot([], patientA, "TAMIN");
  slots = upsertPatientSlot(slots, patientB, "NONE");
  slots = addLineToPatient(slots, "p-a", line("l1"));
  slots = addLineToPatient(slots, "p-b", line("l2"));
  slots = addLineToPatient(slots, "p-a", line("l3"));

  assert.equal(slots.length, 2);
  assert.equal(slots[0].lines.length, 2);
  assert.equal(slots[1].lines.length, 1);
  assert.equal(slots[0].insuranceCode, "TAMIN");

  slots = removeLineFromPatient(slots, "p-a", slots[0].lines[0].key);
  assert.equal(slots[0].lines.length, 1);

  slots = removePatientSlot(slots, "p-b");
  assert.equal(slots.length, 1);
  assert.equal(slots[0].patient.patient_profile_id, "p-a");
});

test("createCartSlot defaults insurance to NONE", () => {
  const slot = createCartSlot(patientA);
  assert.equal(slot.insuranceCode, "NONE");
  assert.equal(slot.lines.length, 0);
});
