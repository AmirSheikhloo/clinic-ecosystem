import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  blankProfile,
  canAutoPrint,
  markDisconnected,
  markEnrolledAfterTestPrint,
} from "./workstationPrinter";

describe("workstationPrinter config", () => {
  it("defaults to 80mm and unknown health", () => {
    const p = blankProfile("ws-1");
    assert.equal(p.widthMm, 80);
    assert.equal(p.health, "UNKNOWN");
    assert.equal(p.adapter, "simulated");
  });

  it("disconnect clears auto-print eligibility", () => {
    const enrolled = markEnrolledAfterTestPrint(
      { ...blankProfile("ws-1"), printerName: "T", autoPrintAfterCommit: true },
      "j1",
    );
    assert.equal(canAutoPrint(enrolled), true);
    const disc = markDisconnected(enrolled);
    assert.equal(canAutoPrint(disc), false);
  });
});
