/**
 * Exercises dashboard, patients, appointments, catalog against real BFF + API + PG15.
 */
import { expect, test } from "@playwright/test";
import {
  assertNoNonLatinDigits,
  assertRtlDocument,
  loginAsReceptionist,
  navLink,
  requireCreds,
} from "./helpers";

test.describe.configure({ mode: "serial" });

test("workspace screens load authorized synthetic data with Latin digits", async ({
  page,
}) => {
  requireCreds();
  await loginAsReceptionist(page);
  await assertRtlDocument(page);

  // Dashboard
  await navLink(page, "داشبورد").click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-count")).toBeVisible();
  const dashCount = await page.getByTestId("dashboard-count").innerText();
  expect(dashCount === "…" || /^\d+$/.test(dashCount)).toBe(true);
  await assertNoNonLatinDigits(page);

  // Patients — register + search
  await navLink(page, "بیماران").click();
  await expect(page.getByTestId("patients-page")).toBeVisible({ timeout: 30_000 });
  const first = "SynWS";
  const last = `P${Date.now().toString().slice(-5)}`;
  await page.getByTestId("patients-new").click();
  await page.getByTestId("patients-first-name").fill(first);
  await page.getByTestId("patients-last-name").fill(last);
  await page.getByTestId("patients-register-submit").click();
  await expect(page.getByTestId("patients-status")).toContainText("بیمار ثبت شد", {
    timeout: 30_000,
  });
  await page.getByTestId("patients-search-query").fill(first);
  await page.getByTestId("patients-search-submit").click();
  await expect(page.getByTestId("patients-result-row").first()).toContainText(first, {
    timeout: 30_000,
  });
  await assertNoNonLatinDigits(page);

  // Appointments
  await navLink(page, "تقویم نوبت‌ها").click();
  await expect(page.getByTestId("appointments-page")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("appointments-count")).toBeVisible();
  const countText = await page.getByTestId("appointments-count").innerText();
  expect(countText).toMatch(/^\d+$/);
  await assertNoNonLatinDigits(page);

  // Catalog
  await navLink(page, "خدمات و منابع").click();
  await expect(page.getByTestId("catalog-page")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Tenant A Consultation")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Room Alpha")).toBeVisible();
  await assertNoNonLatinDigits(page);
});
