/**
 * Patient registry, appointment calendar lifecycle, dashboard and global search
 * against real BFF + API + PG15. Synthetic data only.
 */
import { expect, test } from "@playwright/test";
import { jalaliParts } from "../lib/calendar/jalali-grid";
import { tehranTodayYmd } from "../lib/tehran";
import { assertNoNonLatinDigits } from "./helpers";
import { fillJalaliDateTime } from "./jalali-helpers";
import {
  RUN,
  bff,
  credsFromEnv,
  deskBook,
  deskRegisterPatient,
  expectToast,
  gotoNav,
  loginAs,
  tehranSlot,
} from "./ops-helpers";

test.describe.configure({ mode: "serial" });

const first = "OpsPat";
const last = `Reg${RUN}`;

test("manager: patient registry — register, search, profile edit, deactivate", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await gotoNav(page, "بیماران", "patients-page");

  await page.getByTestId("patients-new").click();
  await page.getByTestId("patients-first-name").fill(first);
  await page.getByTestId("patients-last-name").fill(last);
  await page.getByTestId("patients-register-submit").click();
  await expect(page.getByTestId("patients-status")).toContainText("بیمار ثبت شد", { timeout: 30_000 });
  await expectToast(page, "بیمار با موفقیت ثبت شد");

  await page.getByTestId("patients-search-query").fill(last);
  await page.getByTestId("patients-search-submit").click();
  const row = page.getByTestId("patients-result-row").filter({ hasText: last });
  await expect(row).toHaveCount(1);
  await row.getByTestId("patients-open-profile").click();

  await expect(page.getByTestId("patient-profile-page")).toBeVisible();
  await expect(page.getByTestId("patient-first-name")).toHaveValue(first);
  await page.getByTestId("patient-dossier").fill(`D-${RUN}`);
  await page.getByTestId("patient-save").click();
  await expectToast(page, "اطلاعات بیمار به‌روزرسانی شد");
  await expect(page.getByTestId("patient-dossier")).toHaveValue(`D-${RUN}`);

  await expect(page.getByTestId("patient-history")).toContainText("هنوز نوبتی");

  await page.getByTestId("patient-toggle-active").click();
  await page.getByTestId("patient-toggle-dialog-confirm").click();
  await expectToast(page, "بیمار غیرفعال شد");
  await expect(page.getByTestId("patient-book")).toHaveCount(0);
  await page.getByTestId("patient-toggle-active").click();
  await page.getByTestId("patient-toggle-dialog-confirm").click();
  await expectToast(page, "بیمار فعال شد");
  await expect(page.getByTestId("patient-book")).toBeVisible();

  // Inactive patients are hidden from the default directory view.
  await page.getByTestId("patient-toggle-active").click();
  await page.getByTestId("patient-toggle-dialog-confirm").click();
  await expectToast(page, "بیمار غیرفعال شد");
  await page.goto("/patients");
  await page.getByTestId("patients-search-query").fill(last);
  await page.getByTestId("patients-search-submit").click();
  await expect(page.getByTestId("patients-result-row").filter({ hasText: last })).toHaveCount(0);
  await page.getByTestId("patients-status-filter").selectOption("inactive");
  await expect(page.getByTestId("patients-result-row").filter({ hasText: last })).toHaveCount(1);
  await assertNoNonLatinDigits(page);
});

test("manager: calendar views, details, reschedule with overlap acknowledgement, cancel", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  const pFirst = "CalPat";
  const pLast = `A${RUN}`;
  const slotA = tehranSlot(0, 17);

  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await deskRegisterPatient(page, pFirst, pLast);
  await deskBook(page, slotA);
  await expect(page.getByTestId("desk-status")).toContainText("نوبت ثبت شد", { timeout: 45_000 });

  // Second patient booked on the same resource and slot needs explicit acknowledgement.
  await deskRegisterPatient(page, "CalPat", `B${RUN}`);
  await deskBook(page, slotA);
  await expect(page.getByTestId("overlap-dialog")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("overlap-confirm").click();
  await expect(page.getByTestId("desk-status")).toContainText("تأیید تداخل", { timeout: 45_000 });

  await gotoNav(page, "تقویم نوبت‌ها", "appointments-page");
  const rowsA = page.getByTestId("appointment-row").filter({ hasText: pLast });
  await expect(rowsA).toHaveCount(1, { timeout: 30_000 });
  await expect(page.getByTestId("appointments-count")).toHaveText(/^\d+$/);

  // Week and month views show the same appointment.
  await page.getByTestId("view-week").click();
  await expect(page.getByTestId("week-view")).toBeVisible();
  await expect(page.getByTestId("week-item").filter({ hasText: pLast })).toHaveCount(1);
  await page.getByTestId("view-month").click();
  await expect(page.getByTestId("month-view")).toBeVisible();
  const populated = page.getByTestId("month-cell").and(page.locator('[data-count]:not([data-count="0"])'));
  await expect(populated.first()).toBeVisible();
  await expect(page.getByTestId("calendar-title")).toContainText(/\d{4}/);
  await assertNoNonLatinDigits(page);

  // Month navigation and Jalali jump work and keep Latin digits.
  const yearBefore = jalaliParts(tehranTodayYmd()).jy;
  await page.getByTestId("appointments-date").fill(`${yearBefore + 1}/01/15`);
  await expect(page.getByTestId("calendar-title")).toContainText(String(yearBefore + 1));
  await page.getByTestId("calendar-today").click();
  await expect(page.getByTestId("calendar-title")).toContainText(String(yearBefore));

  // Filter by status narrows to zero without errors.
  await page.getByTestId("view-day").click();
  await page.getByTestId("filter-status").selectOption("CANCELLED");
  await expect(page.getByTestId("appointment-row")).toHaveCount(0);
  await page.getByTestId("filter-status").selectOption("");
  await expect(rowsA).toHaveCount(1);

  // Details dialog, then reschedule B onto A's slot to force an overlap acknowledgement.
  const rowB = page.getByTestId("appointment-row").filter({ hasText: `B${RUN}` });
  await rowB.getByTestId("appointment-open").click();
  const dialog = page.getByTestId("appointment-dialog");
  await expect(dialog).toContainText(`B${RUN}`);
  await expect(dialog.getByTestId("appointment-allocations")).toContainText("Room Alpha");
  await dialog.getByTestId("appointment-reschedule").click();
  await fillJalaliDateTime(page, "reschedule-start", tehranSlot(0, 19));
  await dialog.getByTestId("reschedule-submit").click();
  await expectToast(page, "نوبت جابه‌جا شد");
  await expect(page.getByTestId("appointment-dialog")).toHaveCount(0);

  // Reschedule back onto A: server demands acknowledgement; dialog lists the conflict.
  await page.getByTestId("appointment-row").filter({ hasText: `B${RUN}` }).getByTestId("appointment-open").click();
  await page.getByTestId("appointment-reschedule").click();
  await fillJalaliDateTime(page, "reschedule-start", slotA);
  await page.getByTestId("reschedule-submit").click();
  await expect(page.getByTestId("overlap-dialog")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("overlap-dialog")).toContainText(`A${RUN}`);
  await page.getByTestId("overlap-confirm").click();
  await expectToast(page, "نوبت جابه‌جا شد");

  // Cancel B.
  await page.getByTestId("appointment-row").filter({ hasText: `B${RUN}` }).getByTestId("appointment-open").click();
  await page.getByTestId("appointment-cancel").click();
  await page.getByTestId("cancel-reason").fill("synthetic cancel");
  await page.getByTestId("cancel-confirm").click();
  await expectToast(page, "نوبت لغو شد");
  await page.getByTestId("filter-status").selectOption("CANCELLED");
  await expect(page.getByTestId("appointment-row").filter({ hasText: `B${RUN}` })).toHaveCount(1);

  // Patient-to-appointment navigation: patient profile history links back to the calendar.
  await page.getByTestId("filter-status").selectOption("");
  await page.getByTestId("appointment-row").filter({ hasText: `A${RUN}` }).getByTestId("appointment-open").click();
  await page.getByTestId("appointment-patient-link").click();
  await expect(page.getByTestId("patient-profile-page")).toBeVisible();
  await expect(page.getByTestId("patient-history-row")).toHaveCount(1);
  await page.getByTestId("history-calendar-link").click();
  await expect(page.getByTestId("appointments-page")).toBeVisible();
  await expect(page.getByTestId("appointment-row").filter({ hasText: `A${RUN}` })).toHaveCount(1);
});

test("manager: dashboard shows real counts and global search finds authorized records", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await gotoNav(page, "داشبورد", "dashboard-page");
  for (const id of ["dashboard-count", "dashboard-patients", "dashboard-staff", "dashboard-services", "dashboard-resources"]) {
    await expect(page.getByTestId(id)).toHaveText(/^\d+$/, { timeout: 30_000 });
  }
  expect(Number(await page.getByTestId("dashboard-count").innerText())).toBeGreaterThanOrEqual(2);
  expect(Number(await page.getByTestId("dashboard-patients").innerText())).toBeGreaterThanOrEqual(2);

  // "/" focuses the global search; results navigate to the patient profile.
  await page.locator("body").click();
  await page.keyboard.press("/");
  await expect(page.getByTestId("global-search-input")).toBeFocused();
  await page.getByTestId("global-search-input").fill(`A${RUN}`);
  const hit = page.getByTestId("global-search-hit").filter({ hasText: `A${RUN}` });
  await expect(hit).toHaveCount(1, { timeout: 15_000 });
  await hit.click();
  await expect(page.getByTestId("patient-profile-page")).toBeVisible();

  // "/" inside an input must type a slash, not steal focus.
  await page.getByTestId("patient-dossier").fill("a/b");
  await expect(page.getByTestId("patient-dossier")).toHaveValue("a/b");

  const summary = await bff(page, "GET", `/api/v1/search?q=${encodeURIComponent(`A${RUN}`)}`);
  expect(summary.status).toBe(200);
  await assertNoNonLatinDigits(page);
});
