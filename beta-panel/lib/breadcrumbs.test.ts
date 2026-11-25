import assert from "node:assert/strict";
import test from "node:test";
import { breadcrumbsFor } from "./breadcrumbs.ts";

test("top-level screens have a single current crumb", () => {
  assert.deepEqual(breadcrumbsFor("/dashboard"), [{ label: "داشبورد" }]);
  assert.deepEqual(breadcrumbsFor("/appointments"), [{ label: "تقویم نوبت‌ها" }]);
});

test("nested screens link back to their workspace", () => {
  assert.deepEqual(breadcrumbsFor("/patients/abc"), [
    { label: "بیماران", href: "/patients" },
    { label: "پروندهٔ بیمار" },
  ]);
  assert.deepEqual(breadcrumbsFor("/catalog/manage"), [
    { label: "خدمات و منابع", href: "/catalog" },
    { label: "مدیریت" },
  ]);
});

test("unknown paths fall back to the product name", () => {
  assert.deepEqual(breadcrumbsFor("/nope"), [{ label: "پنل کلینیک" }]);
});
