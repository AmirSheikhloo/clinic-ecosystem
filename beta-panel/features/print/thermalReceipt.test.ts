import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildThermalReceiptText, simulatedThermalPrint } from "./thermalReceipt";

describe("thermalReceipt", () => {
  it("builds synthetic 80mm receipt without national id", () => {
    const text = buildThermalReceiptText({
      clinicName: "کلینیک نمونه",
      invoiceNumber: "INV-1",
      jalaliDate: "1404/09/06",
      patientDisplay: "مریم احمدی",
      lines: [{ description: "ویزیت", amountIrr: 500_000 }],
      totalPayableIrr: 500_000,
      paidIrr: 500_000,
      methodLabel: "نقدی",
    });
    assert.match(text, /مریم احمدی/);
    assert.match(text, /نمونه مصنوعی/);
    assert.doesNotMatch(text, /کد ملی/);
  });

  it("simulated adapter does not claim hardware", async () => {
    const result = await simulatedThermalPrint("x");
    assert.equal(result.mode, "simulated");
    assert.equal(result.ok, true);
  });
});
