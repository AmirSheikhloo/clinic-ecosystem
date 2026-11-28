import { expect, type Page } from "@playwright/test";
import { tehranTodayYmd } from "../lib/tehran";
import { assertHttpOnlySession, navLink } from "./helpers";
import { fillJalaliDateTime } from "./jalali-helpers";

const CSRF = "ce_beta_csrf";

export type Creds = { login: string; password: string };

export const RUN = Date.now().toString().slice(-6);

export function credsFromEnv(prefix: "OWNER" | "MANAGER" | "DEPUTY"): Creds {
  return {
    login: process.env[`BETA02_${prefix}_LOGIN`] || "",
    password: process.env[`BETA02_${prefix}_PASSWORD`] || "",
  };
}

export function receptionistCreds(): Creds {
  return {
    login: process.env.BETA01B_RECEPTIONIST_LOGIN || "",
    password: process.env.BETA01B_RECEPTIONIST_PASSWORD || "",
  };
}

export function requireOpsCreds(creds: Creds, label: string) {
  if (!creds.login || !creds.password) {
    throw new Error(`Missing ${label} credentials for operations browser E2E`);
  }
}

export async function loginAs(page: Page, creds: Creds, label = "user") {
  requireOpsCreds(creds, label);
  await page.goto("/login");
  await page.evaluate(async () => {
    await fetch("/api/auth/csrf", { method: "GET", credentials: "same-origin" });
  });
  await expect
    .poll(async () => (await page.context().cookies()).some((c) => c.name === CSRF && c.value))
    .toBe(true);
  await page.getByTestId("login-identifier").fill(creds.login);
  await page.getByTestId("login-password").fill(creds.password);
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL(/\/(dashboard|desk)/, { timeout: 45_000 });
  await expect(page.getByTestId("app-sidebar").or(page.getByTestId("desk-page"))).toBeVisible({
    timeout: 45_000,
  });
  await assertHttpOnlySession(page);
}

/** Same-origin BFF call using the browser's cookies and CSRF token. */
export async function bff(
  page: Page,
  method: string,
  path: string,
  options: { body?: unknown; headers?: Record<string, string>; csrf?: boolean } = {},
): Promise<{ status: number; body: Record<string, unknown> | null }> {
  return page.evaluate(
    async ({ method, path, body, headers, csrf }) => {
      const token = decodeURIComponent(
        document.cookie.split("; ").find((c) => c.startsWith("ce_beta_csrf="))?.split("=")[1] ?? "",
      );
      const response = await fetch(path, {
        method,
        credentials: "same-origin",
        headers: {
          "content-type": "application/json",
          ...(csrf === false ? {} : { "x-csrf-token": token }),
          ...(headers ?? {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    },
    { method, path, body: options.body, headers: options.headers, csrf: options.csrf },
  );
}

export async function gotoNav(page: Page, linkName: string, testId: string) {
  // Scope to the main sidebar — dashboard/in-page CTAs reuse the same labels (e.g. مدیریت نوبت‌ها).
  await navLink(page, linkName).click();
  await expect(page.getByTestId(testId)).toBeVisible({ timeout: 30_000 });
}

export function tehranSlot(offsetMinutes = 0, hour = 16): string {
  const minute = String((Math.floor(Date.now() / 60_000) % 40) + offsetMinutes).padStart(2, "0");
  return `${tehranTodayYmd()}T${String(hour).padStart(2, "0")}:${minute}`;
}

export async function deskRegisterPatient(page: Page, first: string, last: string) {
  // After a booking confirmation the desk stays on stage 2 — reset to identification first.
  const nextPatient = page.getByTestId("desk-next-patient");
  if (await nextPatient.first().isVisible().catch(() => false)) {
    await nextPatient.first().click();
  }
  const stage1 = page.getByTestId("desk-stage-1");
  if (await stage1.isVisible().catch(() => false)) {
    await stage1.click();
  }
  await expect(page.getByTestId("patient-first-name")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("patient-first-name").fill(first);
  await page.getByTestId("patient-last-name").fill(last);
  // Identity is required for submit readiness; use the approved exception path (no forged ID).
  await page.getByTestId("desk-identity-exception").click();
  await page.getByTestId("patient-identity-exception").fill(`e2e synthetic ${Date.now().toString().slice(-6)}`);
  await expect(page.getByTestId("patient-register-submit")).toBeEnabled({ timeout: 10_000 });
  await page.getByTestId("patient-register-submit").click();
  await expect(page.getByTestId("desk-status")).toContainText("بیمار ثبت شد", { timeout: 30_000 });
  // Stage advances to booking; summary and cashier both show the name — assert one match.
  await expect(
    page
      .getByTestId("summary-patient")
      .or(page.getByTestId("invoice-patient"))
      .or(page.getByTestId("selected-patient"))
      .filter({ hasText: `${first} ${last}` })
      .first(),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("desk-stage-booking").or(page.getByTestId("desk-stage-2")).first()).toBeVisible();
}

/** Prefer the sr-only native <select> backing SearchableCombobox; fall back to listbox. */
export async function pickComboboxOption(page: Page, testId: string, label: string) {
  const native = page.getByTestId(testId);
  const isSelect = await native.evaluate((el) => el.tagName.toLowerCase() === "select").catch(() => false);
  if (isSelect) {
    await native.selectOption({ label });
  } else {
    const input = page.getByTestId(`${testId}-input`);
    await input.click();
    await input.fill(label);
    // Prefer the visible listbox option — a hidden native <select> also exposes role=option.
    const listbox = page.getByRole("listbox");
    await listbox
      .getByRole("option", { name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) })
      .first()
      .click();
  }
  // Desk autofocus can leave the APG listbox open after a native selectOption — dismiss it.
  const openList = page.getByRole("listbox");
  if ((await openList.count()) > 0) {
    await page.keyboard.press("Escape");
  }
  await expect(openList).toHaveCount(0);
}

/** Dense demo days often collide; accept either a clean booking or an acknowledged overlap. */
export async function acknowledgeIfAsked(page: Page) {
  const dialog = page.getByTestId("overlap-dialog");
  const status = page.getByTestId("desk-status");
  await expect(dialog.or(status)).toBeVisible({ timeout: 45_000 });
  if (await dialog.isVisible()) {
    await page.getByTestId("overlap-confirm").click();
    await expect(status).toContainText(/تأیید تداخل|نوبت ثبت شد/, { timeout: 45_000 });
  } else {
    await expect(status).toContainText("نوبت ثبت شد", { timeout: 45_000 });
  }
}

/** Find a patient row on the dense daily list via the search box. */
export async function findAppointmentRow(page: Page, patientToken: string) {
  await page.getByTestId("list-search").fill(patientToken);
  const row = page.getByTestId("appointment-row").filter({ hasText: patientToken });
  await expect(row).toHaveCount(1, { timeout: 30_000 });
  return row;
}

export async function deskBook(page: Page, startLocal: string) {
  const service = process.env.BETA01B_SERVICE_NAME || "Tenant A Consultation";
  const resourceName = process.env.BETA01B_RESOURCE_NAME || "Room Alpha";
  await pickComboboxOption(page, "service-select", service);
  await expect(page.getByTestId("resource-fieldset")).toBeEnabled({ timeout: 30_000 });
  // Ensure no sticky service listbox covers the resource checkboxes.
  await expect(page.getByRole("listbox")).toHaveCount(0);
  const resource = page.getByTestId("resource-option").filter({ hasText: resourceName });
  await expect(resource).toBeVisible();
  const checkbox = resource.locator('input[type="checkbox"]');
  // Force bypasses residual popover hit-testing; still assert checked state afterward.
  await checkbox.check({ force: true });
  await expect(checkbox).toBeChecked();
  await fillJalaliDateTime(page, "appointment-start", startLocal);
  await expect(page.getByTestId("appointment-submit")).toBeEnabled({ timeout: 15_000 });
  await page.getByTestId("appointment-submit").click();
}

export async function expectToast(page: Page, text: string) {
  await expect(page.getByTestId("toast-item").filter({ hasText: text }).first()).toBeVisible({
    timeout: 20_000,
  });
}
