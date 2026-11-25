/** Role-aware dashboard compositions and deep links (synthetic data). */
import { expect, test } from "@playwright/test";
import { shiftTehranYmd, tehranTodayYmd } from "../lib/tehran";
import { credsFromEnv, loginAs, receptionistCreds } from "./ops-helpers";

test.describe.configure({ mode: "serial" });

test("receptionist sees an operational dashboard without staff/catalog admin metrics", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-dashboard", "operational");
  await expect(page.getByTestId("dashboard-greeting")).toBeVisible();
  await expect(page.getByTestId("dashboard-clock")).toBeVisible();
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-tomorrow")).toBeVisible();
  await expect(page.getByTestId("dashboard-cancelled")).toBeVisible();
  await expect(page.getByTestId("dashboard-staff")).toHaveCount(0);
  await expect(page.getByTestId("dashboard-services")).toHaveCount(0);
  await expect(page.getByTestId("dashboard-resources")).toHaveCount(0);
  await expect(page.getByTestId("dashboard-quick-actions")).toContainText("نوبت‌دهی");
});

test("owner sees management composition with authorized admin metrics", async ({ page }) => {
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-dashboard", "management");
  await expect(page.getByTestId("dashboard-role")).toContainText("مالک");
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-staff")).toBeVisible();
  await expect(page.getByTestId("dashboard-services")).toBeVisible();
});

test("metric cards deep-link to filtered appointment views", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-tomorrow")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("dashboard-tomorrow").click();
  await expect(page).toHaveURL(new RegExp(`date=${shiftTehranYmd(tehranTodayYmd(), 1)}`));
  await expect(page.getByTestId("appointments-page")).toBeVisible();
  await page.goto("/dashboard");
  await page.getByTestId("dashboard-cancelled").click();
  await expect(page).toHaveURL(/status=CANCELLED/);
  await expect(page.getByTestId("filter-status")).toHaveValue("CANCELLED");
});

test("patient register quick action opens the register dialog", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await page.getByRole("link", { name: "ثبت بیمار" }).click();
  await expect(page.getByTestId("patients-register-dialog")).toBeVisible({ timeout: 20_000 });
});
