/**
 * List-first appointment management: book → list → check-in → complete,
 * plus dashboard upcoming rows. Synthetic data only.
 */
import { expect, test } from "@playwright/test";
import {
  RUN,
  credsFromEnv,
  deskBook,
  deskRegisterPatient,
  expectToast,
  gotoNav,
  loginAs,
  tehranSlot,
} from "./ops-helpers";

test.describe.configure({ mode: "serial" });

async function acknowledgeIfAsked(page: import("@playwright/test").Page) {
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

test("manager: list workspace check-in and complete; dashboard upcoming stays live", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  const first = "LifePat";
  const last = `Lc${RUN}`;
  const slot = tehranSlot(2, 15);

  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await deskRegisterPatient(page, first, last);
  await deskBook(page, slot);
  await acknowledgeIfAsked(page);

  await gotoNav(page, "مدیریت نوبت‌ها", "appointments-page");
  await expect(page.getByTestId("appointments-list")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("view-list")).toHaveAttribute("aria-checked", "true");

  const row = page.getByTestId("appointment-row").filter({ hasText: last });
  await expect(row).toHaveCount(1, { timeout: 30_000 });
  await row.getByTestId("appointment-open").click();

  const dialog = page.getByTestId("appointment-dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("appointment-status")).toContainText("تأییدشده");
  await dialog.getByTestId("appointment-check-in").click();
  await expectToast(page, "حضور ثبت شد");
  await expect(page.getByTestId("appointment-dialog")).toHaveCount(0);

  await row.getByTestId("appointment-open").click();
  await expect(dialog.getByTestId("appointment-status")).toContainText("حضور");
  await dialog.getByTestId("appointment-complete").click();
  await expectToast(page, "نوبت تکمیل شد");

  await page.getByTestId("filter-status").selectOption("COMPLETED");
  await expect(page.getByTestId("appointment-row").filter({ hasText: last })).toHaveCount(1, { timeout: 30_000 });

  await gotoNav(page, "داشبورد", "dashboard-page");
  await expect(page.getByTestId("dashboard-count")).toHaveText(/^\d+$/, { timeout: 30_000 });
  // Upcoming may be empty once today's visits finish; the region itself must still render.
  await expect(page.getByRole("region", { name: "برنامهٔ امروز" })).toBeVisible();
  await expect(page.getByTestId("dashboard-row").or(page.getByText("نوبت پیش‌رویی"))).toBeVisible();
});
