/**
 * Authorization surfaces: UI visibility is advisory, the server enforces.
 * Verifies denied states in the browser and direct BFF/API denial.
 */
import { expect, test } from "@playwright/test";
import {
  RUN,
  bff,
  credsFromEnv,
  gotoNav,
  loginAs,
  receptionistCreds,
} from "./ops-helpers";

test.describe.configure({ mode: "serial" });

test("receptionist: no admin navigation, denied pages, server denies direct API calls", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  const nav = page.getByRole("navigation", { name: "ناوبری اصلی" });
  await expect(nav.getByRole("link", { name: "بیماران", exact: true })).toBeVisible();
  await expect(nav.getByRole("link", { name: "کارکنان", exact: true })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "کاربران و دسترسی", exact: true })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "حسابرسی", exact: true })).toHaveCount(0);

  await page.goto("/staff");
  await expect(page.getByTestId("access-denied")).toBeVisible({ timeout: 30_000 });
  await page.goto("/access");
  await expect(page.getByTestId("access-denied")).toBeVisible({ timeout: 30_000 });
  await page.goto("/audit");
  await expect(page.getByTestId("access-denied")).toBeVisible({ timeout: 30_000 });
  await page.goto("/catalog/manage");
  await expect(page.getByTestId("access-denied")).toBeVisible({ timeout: 30_000 });

  for (const path of [
    "/api/v1/staff",
    "/api/v1/access/accounts",
    "/api/v1/access/roles",
    "/api/v1/access/governance",
    "/api/v1/audit/entries",
    "/api/v1/catalog/admin/services",
    "/api/v1/catalog/admin/resources",
  ]) {
    const response = await bff(page, "GET", path);
    expect(response.status, path).toBe(403);
  }
  const create = await bff(page, "POST", "/api/v1/catalog/admin/services", {
    body: { service_name: `Denied ${RUN}`, default_duration_minutes: 10, default_price_irr: 0 },
    headers: { "Idempotency-Key": `denied-${RUN}-aaaaaaaa` },
  });
  expect(create.status).toBe(403);
  const escalate = await bff(page, "PUT", "/api/v1/access/governance/00000000-0000-4000-8000-000000000000", {
    body: { roles: ["CLINIC_OWNER"] },
  });
  expect(escalate.status).toBe(403);
});

test("BFF proxy: allowlist, CSRF and auth routes", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  const loginViaProxy = await bff(page, "POST", "/api/v1/auth/login", { body: { login_identifier: "x", password: "y" } });
  expect(loginViaProxy.status).toBe(404);
  const unknown = await bff(page, "GET", "/api/v1/health");
  expect(unknown.status).toBe(404);
  const noCsrf = await bff(page, "POST", "/api/v1/staff", { body: {}, csrf: false });
  expect(noCsrf.status).toBe(403);
});

test("deputy: scoped privileges only — access screens yes, catalog admin and profiles no", async ({ page }) => {
  await loginAs(page, credsFromEnv("DEPUTY"), "deputy");
  await gotoNav(page, "کاربران و دسترسی", "access-page");
  await expect(page.getByTestId("tab-accounts")).toBeVisible();
  await expect(page.getByTestId("tab-roles")).toBeVisible();
  await expect(page.getByTestId("tab-governance")).toHaveCount(0);

  await page.goto("/catalog/manage");
  await expect(page.getByTestId("access-denied")).toBeVisible({ timeout: 30_000 });

  const roles = await bff(page, "GET", "/api/v1/access/roles");
  expect(roles.status).toBe(200);
  const governance = await bff(page, "PUT", "/api/v1/access/governance/00000000-0000-4000-8000-000000000000", {
    body: { roles: ["CLINIC_OWNER"] },
  });
  expect(governance.status).toBe(403);
  const profile = await bff(page, "GET", "/api/v1/patients/00000000-0000-4000-8000-000000000000");
  expect(profile.status).toBe(403);
});
