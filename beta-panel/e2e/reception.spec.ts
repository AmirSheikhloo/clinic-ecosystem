/**
 * Real Chromium E2E against Next.js panel + BFF + FastAPI + disposable PG15.
 * Mocked API responses are not used.
 */
import { expect, test, type Page } from "@playwright/test";
import { tehranTodayYmd } from "../lib/tehran";
import { navLink } from "./helpers";
import { fillJalaliDateTime } from "./jalali-helpers";

const loginId = () => process.env.BETA01B_RECEPTIONIST_LOGIN || "";
const password = () => process.env.BETA01B_RECEPTIONIST_PASSWORD || "";
const unauthorizedLogin = () =>
  process.env.BETA01B_UNAUTHORIZED_LOGIN || "clerk-no-perms@beta01b.test";
const unauthorizedPassword = () => process.env.BETA01B_UNAUTHORIZED_PASSWORD || "";
const serviceName = () => process.env.BETA01B_SERVICE_NAME || "Tenant A Consultation";
const resourceName = () => process.env.BETA01B_RESOURCE_NAME || "Room Alpha";
const SESSION = "ce_beta_session";
const CSRF = "ce_beta_csrf";

function requireCreds() {
  if (!loginId() || !password()) {
    throw new Error("Missing receptionist credentials for browser E2E");
  }
}

function tehranSlot(): string {
  const ymd = tehranTodayYmd();
  const minute = String(Math.floor((Date.now() / 60_000) % 50)).padStart(2, "0");
  return `${ymd}T15:${minute}`;
}

async function assertHttpOnlySession(page: Page) {
  const cookies = await page.context().cookies();
  const session = cookies.find((c) => c.name === SESSION);
  expect(session, "HttpOnly session cookie must exist").toBeTruthy();
  expect(session!.httpOnly).toBe(true);
  expect(session!.value.length).toBeGreaterThan(20);
  const jsCookies = await page.evaluate(() => document.cookie);
  expect(jsCookies.includes(SESSION)).toBe(false);
  expect(jsCookies.includes(session!.value)).toBe(false);
}

async function loginAsReceptionist(page: Page) {
  requireCreds();
  await page.goto("/login");
  // Prime CSRF cookie the same way the app does before submit.
  await page.evaluate(async () => {
    await fetch("/api/auth/csrf", { method: "GET", credentials: "same-origin" });
  });
  await expect
    .poll(async () => {
      const cookies = await page.context().cookies();
      return cookies.some((c) => c.name === CSRF && c.value.length > 0);
    })
    .toBe(true);
  await page.getByTestId("login-identifier").fill(loginId());
  await page.getByTestId("login-password").fill(password());
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL(/\/desk/, { timeout: 45_000 });
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await assertHttpOnlySession(page);
}

async function registerAndSelectPatient(page: Page, first: string, last: string) {
  await page.getByTestId("patient-first-name").fill(first);
  await page.getByTestId("patient-last-name").fill(last);
  await page.getByTestId("desk-identity-exception").click();
  await page.getByTestId("patient-identity-exception").fill(`e2e reception ${Date.now().toString().slice(-6)}`);
  await expect(page.getByTestId("patient-register-submit")).toBeEnabled({ timeout: 10_000 });
  await page.getByTestId("patient-register-submit").click();
  await expect(page.getByTestId("desk-status")).toContainText("بیمار ثبت شد", {
    timeout: 30_000,
  });
  await expect(page.getByTestId("selected-patient")).toContainText(`${first} ${last}`);
}

async function bookConsultation(page: Page, startLocal: string) {
  await page.getByTestId("service-select").selectOption({ label: serviceName() });
  await expect(page.getByTestId("resource-fieldset")).toBeEnabled({ timeout: 30_000 });
  const resource = page.getByTestId("resource-option").filter({ hasText: resourceName() });
  await expect(resource).toBeVisible();
  await resource.locator('input[type="checkbox"]').check();
  await fillJalaliDateTime(page, "appointment-start", startLocal);
  await expect(page.getByTestId("appointment-submit")).toBeEnabled({ timeout: 15_000 });
  await page.getByTestId("appointment-submit").click();
}

test.describe.configure({ mode: "serial" });

test("BETA-01B reception browser acceptance gate", async ({ page, request }) => {
  requireCreds();
  const synthFirst = "SynE2E";
  const synthLast = `Pat${Date.now().toString().slice(-6)}`;
  const startLocal = tehranSlot();

  // 1) Unauthenticated visitor redirected to login
  await page.goto("/desk");
  await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });

  // 2–4) Sign in + HttpOnly session
  await loginAsReceptionist(page);

  // Security: missing authentication (no session cookies on isolated request context)
  const unauth = await request.get("/api/appointments");
  expect([401, 403]).toContain(unauth.status());

  // Invalid / missing CSRF on state-changing BFF call (session present)
  const authedMissingCsrf = await page.request.post("/api/appointments", {
    data: { beneficiary_patient_id: "x" },
    headers: { "content-type": "application/json" },
  });
  expect(authedMissingCsrf.status()).toBe(403);

  const csrfCookie = (await page.context().cookies()).find((c) => c.name === CSRF);
  expect(csrfCookie).toBeTruthy();
  const origin = new URL(page.url()).origin;
  const authedBadCsrf = await page.request.post("/api/appointments", {
    data: { beneficiary_patient_id: "x" },
    headers: {
      "content-type": "application/json",
      "x-csrf-token": "not-the-real-csrf-token",
      origin,
    },
  });
  expect(authedBadCsrf.status()).toBe(403);

  // 5–10) Create patient, select service/resources/time, submit (dense demo may require overlap ack)
  await registerAndSelectPatient(page, synthFirst, synthLast);
  await bookConsultation(page, startLocal);
  const overlap = page.getByTestId("overlap-dialog");
  const status = page.getByTestId("desk-status");
  await expect(overlap.or(status)).toBeVisible({ timeout: 45_000 });
  if (await overlap.isVisible()) {
    await page.getByTestId("overlap-confirm").click();
  }
  await expect(status).toContainText(/نوبت ثبت شد|تأیید تداخل/, { timeout: 45_000 });
  const statusText = await status.innerText();
  const idMatch = statusText.match(
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
  );
  expect(idMatch, "appointment id must appear").toBeTruthy();
  const appointmentId = idMatch![0];

  // Duplicate submission of same intent must replay, not create a second row
  await page.getByTestId("appointment-submit").click();
  await expect(status).toContainText(appointmentId, { timeout: 45_000 });
  const statusAfterDup = await status.innerText();
  expect(statusAfterDup).toMatch(/بازیابی تکرار|نوبت ثبت شد|تأیید تداخل/);

  // 11) Daily list shows the appointment once for this synthetic patient
  await navLink(page, "مدیریت نوبت‌ها").click();
  await expect(page).toHaveURL(/\/appointments/);
  await expect(page.getByTestId("appointments-page")).toBeVisible();
  await page.getByTestId("list-search").fill(synthLast);
  const rows = page.getByTestId("appointment-row").filter({ hasText: synthLast });
  await expect(rows).toHaveCount(1, { timeout: 30_000 });
  await expect(rows.first()).toContainText(synthFirst);

  // Overlap confirmation (receptionist has ALLOW_MANUAL_OVERBOOKING)
  await navLink(page, "میز پذیرش").click();
  await expect(page.getByTestId("desk-page")).toBeVisible();
  await registerAndSelectPatient(page, "Overlap", `Case${Date.now().toString().slice(-5)}`);
  await bookConsultation(page, startLocal);
  await expect(page.getByTestId("overlap-dialog")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("overlap-confirm").click();
  await expect(page.getByTestId("desk-status")).toContainText("تأیید تداخل", {
    timeout: 45_000,
  });

  // 12–13) Logout invalidates session; protected requests rejected
  await page.getByTestId("logout-button").click();
  await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  const cookiesAfter = await page.context().cookies();
  const sessionAfter = cookiesAfter.find((c) => c.name === SESSION);
  expect(!sessionAfter || sessionAfter.value === "").toBeTruthy();

  const protectedAfterLogout = await page.request.get("/api/auth/me");
  expect(protectedAfterLogout.status()).toBe(401);

  await page.goto("/desk");
  await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
});

test("unauthorized principal cannot use reception catalog", async ({ page }) => {
  if (!unauthorizedPassword()) {
    throw new Error("Missing unauthorized fixture password for browser E2E");
  }
  await page.goto("/login");
  await page.getByTestId("login-identifier").fill(unauthorizedLogin());
  await page.getByTestId("login-password").fill(unauthorizedPassword());
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL(/\/desk/, { timeout: 30_000 });
  // No catalog permission → boot fails closed (no bookable surface / no cross-tenant leak)
  await expect(page.getByTestId("desk-boot-error")).toBeVisible({ timeout: 45_000 });
  const bootText = await page.getByTestId("desk-boot-error").innerText();
  expect(bootText.length).toBeGreaterThan(0);
  expect(bootText).not.toContain("Tenant B Hidden Service");
});
