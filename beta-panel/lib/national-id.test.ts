import assert from "node:assert/strict";
import test from "node:test";
import { isValidNationalIdChecksum, normalizeNationalIdInput } from "./national-id";

test("normalizeNationalIdInput converts Persian digits", () => {
  assert.equal(normalizeNationalIdInput("۰۰۱۳۵۴۲۴۱۹"), "0013542419");
});

test("checksum accepts known valid id", () => {
  assert.equal(isValidNationalIdChecksum("0013542419"), true);
});

test("checksum rejects repeated digits", () => {
  assert.equal(isValidNationalIdChecksum("0000000000"), false);
});
