/** Role-aware dashboard compositions and metric filters (synthetic data). */
import { expect, test } from "@playwright/test";
import { credsFromEnv, loginAs, receptionistCreds } from "./ops-helpers";

test.describe.configure({ mode: "serial" });

test("receptionist sees an operational dashboard without staff/catalog admin metrics", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-dashboard", "operational");
  await expect(page.getByRole("heading", { name: "میز کار پذیرش" })).toBeVisible();
  await expect(page.getByTestId("dashboard-greeting")).toHaveCount(0);
  // Five operational metric cards; today is non-interactive.
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-upcoming")).toBeVisible();
  await expect(page.getByTestId("dashboard-needs-status")).toBeVisible();
  await expect(page.getByTestId("dashboard-cancelled")).toBeVisible();
  await expect(page.getByTestId("dashboard-online")).toBeVisible();
  await expect(page.getByTestId("dashboard-count-card")).toHaveAttribute("data-interactive", "false");
  await expect(page.getByTestId("dashboard-staff")).toHaveCount(0);
  await expect(page.getByTestId("dashboard-quick-actions")).toContainText("نوبت‌دهی");
  // Metrics appear above quick actions in the DOM.
  const metricsBox = await page.getByTestId("dashboard-metrics").boundingBox();
  const actionsBox = await page.getByTestId("dashboard-quick-actions").boundingBox();
  expect(metricsBox && actionsBox && metricsBox.y < actionsBox.y).toBeTruthy();
});

test("owner sees management composition with authorized admin metrics", async ({ page }) => {
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-dashboard", "management");
  await expect(page.getByRole("heading", { name: "داشبورد مدیریت" })).toBeVisible();
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-staff")).toBeVisible();
  await expect(page.getByTestId("dashboard-patients")).toBeVisible();
});

test("metric cards filter the operational day table in place", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-cancelled")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("dashboard-cancelled").click();
  await expect(page.getByTestId("schedule-title")).toContainText("لغوشده");
  await expect(page.getByTestId("active-metric-chip")).toBeVisible();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByTestId("dashboard-upcoming").click();
  await expect(page.getByTestId("schedule-title")).toContainText("پیش رو");
  await page.getByTestId("active-metric-chip").click();
  await expect(page.getByTestId("schedule-title")).toContainText("امروز");
});

test("patient search quick action opens the patients workspace", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await page.getByRole("link", { name: /جستجوی بیمار/ }).click();
  await expect(page.getByTestId("patients-page")).toBeVisible({ timeout: 20_000 });
});

test("top bar shows full Jalali clock and Persian account without email job line", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  const clock = page.getByTestId("tehran-clock");
  await expect(clock).toBeVisible();
  await expect(clock).toContainText("به وقت تهران");
  await expect(clock).toContainText("·");
  await expect(page.getByTestId("account-job-title")).toBeVisible();
  await expect(page.getByTestId("account-job-title")).not.toContainText("@");
  await expect(page.getByTestId("notification-bell")).toBeVisible();
});
