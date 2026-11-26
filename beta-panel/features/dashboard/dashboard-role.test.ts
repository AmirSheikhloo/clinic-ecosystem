import assert from "node:assert/strict";
import test from "node:test";
import { P } from "../../lib/permissions.ts";
import { resolveDashboardAudience } from "./dashboard-role.ts";

function canOf(...codes: string[]) {
  const set = new Set(codes);
  return (code: string) => set.has(code);
}

test("owner and manager get the management composition", () => {
  assert.equal(resolveDashboardAudience(["CLINIC_OWNER"], canOf(P.appointmentsList, P.staffView)).composition, "management");
  assert.equal(resolveDashboardAudience(["CLINIC_MANAGER"], canOf(P.appointmentsList)).composition, "management");
});

test("general receptionist stays operational without staff metrics privilege path", () => {
  const audience = resolveDashboardAudience(
    ["RECEPTIONIST"],
    canOf(P.appointmentsList, P.appointmentsSchedule, P.patientsSearch, P.patientsRegister),
  );
  assert.equal(audience.composition, "operational");
  assert.equal(audience.headReception, false);
});

test("receptionist with supervision permissions is treated as head reception", () => {
  const audience = resolveDashboardAudience(
    ["RECEPTIONIST"],
    canOf(P.appointmentsList, P.appointmentsSchedule, P.patientsSearch, P.staffView),
  );
  assert.equal(audience.composition, "operational");
  assert.equal(audience.headReception, true);
});
