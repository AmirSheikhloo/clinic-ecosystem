/**
 * Task 34 four-workspace acceptance: finance, waitlist, ops, cashier, dossier.
 */
import { expect, test } from "@playwright/test";
import {
  assertRtlDocument,
  loginAsReceptionist,
  navLink,
  requireCreds,
} from "./helpers";

test.describe.configure({ mode: "serial" });

test("Task 34 workspaces: finance, waitlist, ops, desk cashier, patient dossier", async ({
  page,
}) => {
  requireCreds();
  await loginAsReceptionist(page);
  await assertRtlDocument(page);

  await navLink(page, "امور مالی").click();
  await expect(page.getByTestId("finance-page")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("finance-summary")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("finance-invoices")).toBeVisible();
  const invoice = page.getByTestId("finance-invoice").first();
  await expect(invoice).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("finance-open-invoice").first().click();
  await expect(page.getByTestId("finance-invoice-detail")).toBeVisible({ timeout: 30_000 });

  await navLink(page, "لیست انتظار").click();
  await expect(page.getByTestId("waitlist-page")).toBeVisible({ timeout: 30_000 });

  await navLink(page, "پیکربندی عملیات").click();
  await expect(page.getByTestId("ops-page")).toBeVisible({ timeout: 30_000 });

  await navLink(page, "میز پذیرش").click();
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("cashier-panel")).toBeVisible({ timeout: 30_000 });

  await navLink(page, "بیماران").click();
  await expect(page.getByTestId("patients-page")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("patients-search-query").fill("ا");
  await page.getByTestId("patients-search-submit").click();
  const row = page.getByTestId("patients-result-row").first();
  await expect(row).toBeVisible({ timeout: 30_000 });
  await row.getByTestId("patients-open-profile").click();
  await expect(page).toHaveURL(/\/patients\//, { timeout: 30_000 });
  await expect(page.getByTestId("patient-dossier-ops")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("patient-finance")).toBeVisible();
  await expect(page.getByTestId("patient-notes")).toBeVisible();
  await expect(page.getByTestId("patient-tags")).toBeVisible();
});
