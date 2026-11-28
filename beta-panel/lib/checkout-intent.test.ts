import assert from "node:assert/strict";
import { test } from "node:test";
import { allocateFixedDiscountIrr, CheckoutIntentStore } from "./checkout-intent";

test("CheckoutIntentStore reuses UUID for same fingerprint", () => {
  const store = new CheckoutIntentStore();
  const intent = {
    patientId: "p1",
    lineServiceIds: ["s1", "s2"],
    lineAppointmentIds: ["a1", "a2"],
    discountFixed: 1000,
    discountBps: 0,
    payMethod: "CASH",
    paymentAmountIrr: 9000,
    acceptCredit: false,
    post: true,
  };
  const a = store.keyFor(intent, () => "uuid-a");
  const b = store.keyFor(intent, () => "uuid-b");
  assert.equal(a, "uuid-a");
  assert.equal(b, "uuid-a");
});

test("CheckoutIntentStore issues new key when payload changes", () => {
  const store = new CheckoutIntentStore();
  let n = 0;
  const create = () => `uuid-${++n}`;
  const base = {
    patientId: "p1",
    lineServiceIds: ["s1"],
    lineAppointmentIds: ["a1"] as Array<string | null>,
    discountFixed: 0,
    discountBps: 0,
    payMethod: "CASH",
    paymentAmountIrr: 1000,
    acceptCredit: false,
    post: true,
  };
  const first = store.keyFor(base, create);
  const second = store.keyFor({ ...base, paymentAmountIrr: 2000 }, create);
  assert.equal(first, "uuid-1");
  assert.equal(second, "uuid-2");
  assert.notEqual(first, second);
});

test("CheckoutIntentStore complete allows new purchase with identical payload", () => {
  const store = new CheckoutIntentStore();
  let n = 0;
  const create = () => `uuid-${++n}`;
  const intent = {
    patientId: "p1",
    lineServiceIds: ["s1"],
    lineAppointmentIds: [null] as Array<string | null>,
    discountFixed: 0,
    discountBps: 0,
    payMethod: "NONE",
    paymentAmountIrr: null,
    acceptCredit: false,
    post: true,
  };
  const first = store.keyFor(intent, create);
  store.complete();
  const second = store.keyFor(intent, create);
  assert.equal(first, "uuid-1");
  assert.equal(second, "uuid-2");
});

test("allocateFixedDiscountIrr uses largest remainder and caps", () => {
  assert.deepEqual(allocateFixedDiscountIrr([100, 100, 100], 100), [34, 33, 33]);
  assert.deepEqual(allocateFixedDiscountIrr([1000, 1], 500), [500, 0]);
  assert.deepEqual(allocateFixedDiscountIrr([50, 50], 200), [50, 50]);
  assert.deepEqual(allocateFixedDiscountIrr([], 10), []);
});
