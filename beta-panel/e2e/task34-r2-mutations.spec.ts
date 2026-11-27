/**
 * Task 34 R2 — mutation-focused Playwright E2E (synthetic preview only).
 * Prefer persisted state changes over mere visibility.
 */
import { expect, test, type Page } from "@playwright/test";
import { assertHttpOnlySession, navLink } from "./helpers";
import {
  RUN,
  acknowledgeIfAsked,
  deskBook,
  deskRegisterPatient,
  findAppointmentRow,
  gotoNav,
  tehranSlot,
} from "./ops-helpers";
import { fillJalaliDateTime } from "./jalali-helpers";

test.describe.configure({ mode: "serial" });

const CSRF = "ce_beta_csrf";
const SESSION = "ce_beta_session";
const DEMO_PASSWORD = process.env.BETA01B_DEMO_PASSWORD || "Clinic123!";

async function primeCsrf(page: Page) {
  await page.goto("/login");
  await page.evaluate(async () => {
    await fetch("/api/auth/csrf", { method: "GET", credentials: "same-origin" });
  });
  await expect
    .poll(async () => (await page.context().cookies()).some((c) => c.name === CSRF && c.value))
    .toBe(true);
}

async function loginDemoAlias(page: Page, alias: string) {
  await primeCsrf(page);
  const selector = page.getByTestId("demo-role-selector");
  if (await selector.isVisible().catch(() => false)) {
    await page.getByTestId(`demo-role-${alias}`).click();
  } else {
    // Fail-closed catalogs hide the selector; type the alias + shared password.
    await page.getByTestId("login-identifier").fill(alias);
    await page.getByTestId("login-password").fill(DEMO_PASSWORD);
    await page.getByTestId("login-submit").click();
  }
  await expect(page).toHaveURL(/\/(dashboard|desk)/, { timeout: 45_000 });
  await expect(page.getByTestId("app-sidebar").or(page.getByTestId("desk-page"))).toBeVisible({
    timeout: 45_000,
  });
  await assertHttpOnlySession(page);
}

async function logout(page: Page) {
  const logoutBtn = page.getByTestId("logout-button");
  if (await logoutBtn.isVisible().catch(() => false)) {
    await logoutBtn.click();
  } else {
    await page.evaluate(async () => {
      const token = decodeURIComponent(
        document.cookie.split("; ").find((c) => c.startsWith("ce_beta_csrf="))?.split("=")[1] ?? "",
      );
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
        headers: { "x-csrf-token": token },
      });
    });
    await page.goto("/login");
  }
  await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  const cookies = await page.context().cookies();
  const session = cookies.find((c) => c.name === SESSION);
  expect(!session || !session.value).toBeTruthy();
}

test("R2-MUT-01 receptionist books, checks out, persists after reload", async ({ page }) => {
  const first = "MutR2";
  const last = `Ck${RUN}`;
  const slot = tehranSlot(3, 17);

  await loginDemoAlias(page, "receptionist");
  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });

  await deskRegisterPatient(page, first, last);
  await deskBook(page, slot);
  await acknowledgeIfAsked(page);
  const status = page.getByTestId("desk-status");
  await expect(status).toContainText(/نوبت ثبت شد|تأیید تداخل|گروه پذیرش/, { timeout: 45_000 });
  const statusText = await status.innerText();
  const idMatch = statusText.match(
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
  );
  expect(idMatch, "appointment id must appear after booking").toBeTruthy();
  const appointmentId = idMatch![0];

  // Queue a billable line then mutate via cashier checkout (synthetic CASH only).
  const service = process.env.BETA01B_SERVICE_NAME || "Tenant A Consultation";
  const resourceName = process.env.BETA01B_RESOURCE_NAME || "Room Alpha";
  await page.getByTestId("service-select").selectOption({ label: service });
  await expect(page.getByTestId("resource-fieldset")).toBeEnabled({ timeout: 30_000 });
  const resource = page.getByTestId("resource-option").filter({ hasText: resourceName });
  await resource.locator('input[type="checkbox"]').check();
  await fillJalaliDateTime(page, "appointment-start", tehranSlot(5, 18));
  await expect(page.getByTestId("add-service-line")).toBeEnabled({ timeout: 15_000 });
  await page.getByTestId("add-service-line").click();
  await expect(page.getByTestId("invoice-lines").getByTestId("invoice-line").first()).toBeVisible({
    timeout: 15_000,
  });

  await page.getByTestId("cashier-pay-cash").click();
  await page.getByTestId("cashier-checkout").click();
  await expect(page.getByTestId("cashier-result")).toBeVisible({ timeout: 45_000 });
  const invoiceText = await page.getByTestId("cashier-result").innerText();
  expect(invoiceText).toMatch(/ثبت شد|شماره/);

  // Persist: reload desk then appointments list still shows the booked row.
  await page.reload();
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await gotoNav(page, "مدیریت نوبت‌ها", "appointments-page");
  await findAppointmentRow(page, last);
  await expect(page.getByTestId("appointment-row").filter({ hasText: last }).first()).toContainText(
    first,
  );

  // API-backed confirmation via BFF (same-origin cookies).
  const listed = await page.evaluate(async (token) => {
    const res = await fetch(`/api/appointments?q=${encodeURIComponent(token)}`, {
      credentials: "same-origin",
    });
    return { status: res.status, body: await res.json().catch(() => null) };
  }, last);
  expect(listed.status).toBe(200);
  const blob = JSON.stringify(listed.body ?? {});
  expect(blob).toContain(appointmentId);
});

test("R2-MUT-02 demo role switch clears session and changes permissions", async ({ page }) => {
  await loginDemoAlias(page, "receptionist");
  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByTestId("desk-boot-error")).toHaveCount(0);
  const before = (await page.context().cookies()).find((c) => c.name === SESSION)?.value;
  expect(before && before.length > 20).toBeTruthy();

  await logout(page);

  // Clerk/limited alias: login succeeds but reception catalog fails closed.
  await loginDemoAlias(page, "clerk");
  const after = (await page.context().cookies()).find((c) => c.name === SESSION)?.value;
  expect(after && after !== before).toBeTruthy();

  await page.goto("/desk");
  await expect(page.getByTestId("desk-boot-error").or(page.getByTestId("desk-page"))).toBeVisible({
    timeout: 45_000,
  });
  if (await page.getByTestId("desk-boot-error").isVisible()) {
    const boot = await page.getByTestId("desk-boot-error").innerText();
    expect(boot.length).toBeGreaterThan(0);
  } else {
    // If desk boots, cashier/post must still be denied for clerk.
    await expect(page.getByTestId("cashier-checkout")).toHaveCount(0);
  }

  // Owner alias should see management dashboard composition.
  await logout(page);
  await loginDemoAlias(page, "owner");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 45_000 });
  const composition = await page.getByTestId("dashboard-page").getAttribute("data-dashboard");
  expect(["management", "operational"]).toContain(composition);
  if (composition === "management") {
    await expect(page.getByTestId("dashboard-staff").or(page.getByTestId("dashboard-count"))).toBeVisible({
      timeout: 30_000,
    });
  }
});

test("R2-MUT-03 dashboard metric filter + page size + finance drawer", async ({ page }) => {
  await loginDemoAlias(page, "receptionist");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("dashboard-cancelled").click();
  await expect(page.getByTestId("dashboard-day-total")).toContainText(/cancelled|لغو|پالایه/i, {
    timeout: 30_000,
  });
  // Filter is in-place (hash/server metric), not a hard navigation away from dashboard.
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
  await expect(page.getByTestId("today-schedule")).toBeVisible();

  await page.getByTestId("dashboard-count").click();
  const pageSize = page.getByTestId("dashboard-day-page-size");
  await expect(pageSize).toBeVisible({ timeout: 15_000 });
  await pageSize.selectOption("50");
  await expect(pageSize).toHaveValue("50");
  await pageSize.selectOption("25");
  await expect(pageSize).toHaveValue("25");

  // Prefer opening finance from a dashboard row; fall back to appointments list.
  const dashFinance = page.getByTestId("dashboard-open-finance").first();
  if (await dashFinance.isVisible().catch(() => false)) {
    await dashFinance.click();
  } else {
    await gotoNav(page, "مدیریت نوبت‌ها", "appointments-page");
    const listFinance = page.getByTestId("list-open-finance").first();
    if (await listFinance.isVisible().catch(() => false)) {
      await listFinance.click();
    } else {
      const row = page.getByTestId("appointment-row").first();
      await expect(row).toBeVisible({ timeout: 30_000 });
      await row.getByTestId("appointment-open").click();
      await page.getByTestId("appointment-open-finance").click();
    }
  }
  await expect(
    page.getByTestId("appointment-finance-drawer").or(page.getByTestId("finance-drawer")),
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByTestId("finance-drawer-body").or(page.getByTestId("finance-drawer-invoice")).or(
      page.getByTestId("finance-drawer-empty"),
    ),
  ).toBeVisible({ timeout: 30_000 });
});
