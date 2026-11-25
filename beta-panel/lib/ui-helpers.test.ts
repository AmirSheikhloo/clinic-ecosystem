import assert from "node:assert/strict";
import test from "node:test";
import { NAV_ITEMS, P, activeNav, hasAny, visibleNav } from "./permissions.ts";
import { clampOffset, pageInfo } from "./pagination.ts";
import { isTypingTarget, searchHitHref } from "./search-links.ts";
import { buildQuery } from "./api.ts";

test("navigation is filtered by permission and never grants anything itself", () => {
  const none = new Set<string>();
  assert.deepEqual(visibleNav(none).map((i) => i.href), ["/dashboard", "/preferences"]);

  const reception = new Set([P.patientsSearch, P.appointmentsList, P.appointmentsSchedule, P.catalogServicesRead]);
  assert.deepEqual(
    visibleNav(reception).map((i) => i.href),
    ["/dashboard", "/desk", "/appointments", "/patients", "/catalog", "/preferences"],
  );

  const admin = new Set([P.staffView, P.rolesView]);
  assert.deepEqual(visibleNav(admin).map((i) => i.href), ["/dashboard", "/staff", "/access", "/preferences"]);
  assert.equal(hasAny(none, []), true);
  assert.equal(hasAny(none, [P.staffView]), false);
});

test("the calendar nav label is stable", () => {
  assert.equal(NAV_ITEMS.find((i) => i.href === "/appointments")?.label, "تقویم نوبت‌ها");
});

test("activeNav matches by path segment, not raw prefix", () => {
  assert.equal(activeNav("/patients/abc")?.href, "/patients");
  assert.equal(activeNav("/patientsX")?.href, undefined);
  assert.equal(activeNav("/catalog/manage")?.href, "/catalog");
});

test("pagination helpers", () => {
  assert.deepEqual(pageInfo(0, 20, 0), { pages: 1, page: 1, from: 0, to: 0 });
  assert.deepEqual(pageInfo(45, 20, 40), { pages: 3, page: 3, from: 41, to: 45 });
  assert.equal(clampOffset(45, 20, 100), 40);
  assert.equal(clampOffset(0, 20, 100), 0);
  assert.equal(clampOffset(45, 20, 20), 20);
});

test("search hit links encode untrusted text", () => {
  assert.equal(searchHitHref({ kind: "patient", id: "a/b", title: "x", subtitle: null }), "/patients/a%2Fb");
  assert.equal(
    searchHitHref({ kind: "staff", id: "1", title: "علی & رضا?", subtitle: null }),
    `/staff?q=${encodeURIComponent("علی & رضا?")}`,
  );
  assert.equal(isTypingTarget({ tagName: "input" } as unknown as EventTarget), true);
  assert.equal(isTypingTarget({ tagName: "DIV" } as unknown as EventTarget), false);
  assert.equal(isTypingTarget(null), false);
});

test("buildQuery skips empty values and encodes", () => {
  assert.equal(buildQuery({ q: "", a: undefined, b: null }), "");
  assert.equal(buildQuery({ q: "a b", limit: 20, flag: false }), "?q=a+b&limit=20&flag=false");
});

test("describeError maps codes to Persian and never leaks raw English text", async () => {
  const { describeError } = await import("./error-messages.ts");
  assert.match(describeError("privilege_escalation_denied", "Cannot grant", "x"), /مجوزی/);
  assert.equal(describeError("unknown_code", "Some English text", "پیام عمومی"), "پیام عمومی");
  assert.equal(describeError("unknown_code", "خطای فارسی", "x"), "خطای فارسی");
  assert.equal(describeError(undefined, undefined, "fallback"), "fallback");
});
