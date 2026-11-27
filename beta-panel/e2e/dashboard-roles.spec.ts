/** Role-aware dashboard compositions and metric filters (synthetic data). */
import { expect, test } from "@playwright/test";
import { credsFromEnv, loginAs, receptionistCreds } from "./ops-helpers";

test.describe.configure({ mode: "serial" });

test("receptionist sees an operational dashboard without staff/catalog admin metrics", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-dashboard", "operational");
  await expect(page.getByTestId("dashboard-greeting")).toBeVisible();
  await expect(page.getByTestId("dashboard-clock")).toBeVisible();
  // Task 34 §8: exactly four operational metric cards.
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-upcoming")).toBeVisible();
  await expect(page.getByTestId("dashboard-needs-status")).toBeVisible();
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
  await expect(page.getByTestId("dashboard-patients")).toBeVisible();
});

test("metric cards filter the operational day table in place", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-cancelled")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("dashboard-cancelled").click();
  await expect(page.getByTestId("dashboard-day-total")).toContainText("cancelled");
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByTestId("dashboard-upcoming").click();
  await expect(page.getByTestId("dashboard-day-total")).toContainText("upcoming");
});

test("patient search quick action opens the patients workspace", async ({ page }) => {
  await loginAs(page, receptionistCreds(), "receptionist");
  await page.goto("/dashboard");
  await page.getByRole("link", { name: /جستجوی بیمار/ }).click();
  await expect(page.getByTestId("patients-page")).toBeVisible({ timeout: 20_000 });
});
