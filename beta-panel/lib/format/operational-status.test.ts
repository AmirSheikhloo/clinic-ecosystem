import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  financialStatusFa,
  operationalPresentation,
  operationalStatusLabel,
} from "./operational-status";

describe("operational presentation", () => {
  it("maps domain statuses to PO-approved labels", () => {
    assert.equal(operationalStatusLabel(operationalPresentation("CONFIRMED")), "در انتظار");
    assert.equal(operationalStatusLabel(operationalPresentation("COMPLETED")), "انجام‌شده");
    assert.equal(operationalStatusLabel(operationalPresentation("CANCELLED")), "لغوشده");
    assert.equal(operationalStatusLabel(operationalPresentation("NO_SHOW")), "انجام‌نشده");
    assert.equal(
      operationalStatusLabel(operationalPresentation("CONFIRMED", { needsStatus: true })),
      "نیازمند تعیین وضعیت",
    );
  });

  it("localizes financial codes and never returns raw UNPAID as the label", () => {
    assert.equal(financialStatusFa("PAID"), "پرداخت‌شده");
    assert.equal(financialStatusFa("UNPAID"), "پرداخت‌نشده");
    assert.equal(financialStatusFa("PARTIAL"), "پرداخت ناقص");
    assert.notEqual(financialStatusFa("UNPAID"), "UNPAID");
  });
});
