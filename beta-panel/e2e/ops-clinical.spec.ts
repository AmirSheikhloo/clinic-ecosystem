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
  acknowledgeIfAsked,
  deskRegisterPatient,
  expectToast,
  findAppointmentRow,
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
  await page.getByTestId("identity-type-exception").click();
  await page.getByTestId("patients-identity-exception").fill(`e2e clinical ${RUN}`);
  await expect(page.getByTestId("patients-register-submit")).toBeEnabled({ timeout: 10_000 });
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
  const slotA = tehranSlot(0, 22);

  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await deskRegisterPatient(page, pFirst, pLast);
  await deskBook(page, slotA);
  await acknowledgeIfAsked(page);

  // Second patient booked on the same resource and slot needs explicit acknowledgement.
  await deskRegisterPatient(page, "CalPat", `B${RUN}`);
  await deskBook(page, slotA);
  await expect(page.getByTestId("overlap-dialog")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("overlap-confirm").click();
  await expect(page.getByTestId("desk-status")).toContainText("تأیید تداخل", { timeout: 45_000 });

  await page.goto("/appointments?view=list");
  await expect(page.getByTestId("appointments-page")).toBeVisible({ timeout: 30_000 });
  await findAppointmentRow(page, pLast);
  await expect(page.getByTestId("appointments-count")).toHaveText(/^\d+$/);

  // Week/day calendars truncate on dense demo weeks — filter Room Alpha first.
  await page.getByTestId("view-day").click();
  await page.getByTestId("filter-resource").selectOption({ label: process.env.BETA01B_RESOURCE_NAME || "Room Alpha" });
  await expect(page.getByTestId("timeline-event").filter({ hasText: pLast })).toHaveCount(1, { timeout: 30_000 });
  await page.getByTestId("view-week").click();
  await expect(page.getByTestId("week-view")).toBeVisible();
  await expect(page.getByTestId("week-item").filter({ hasText: pLast })).toHaveCount(1, { timeout: 30_000 });
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

  // Filter by status narrows to zero without errors; then return to list + search.
  await page.getByTestId("view-day").click();
  await page.getByTestId("filter-status").selectOption("CANCELLED");
  await expect(page.getByTestId("appointment-row").or(page.getByTestId("timeline-event"))).toHaveCount(0);
  await page.getByTestId("filter-status").selectOption("");
  await page.getByTestId("view-list").click();
  await findAppointmentRow(page, pLast);

  // Details dialog, then reschedule B onto A's slot to force an overlap acknowledgement.
  const rowB = await findAppointmentRow(page, `B${RUN}`);
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
  await (await findAppointmentRow(page, `B${RUN}`)).getByTestId("appointment-open").click();
  await page.getByTestId("appointment-reschedule").click();
  await fillJalaliDateTime(page, "reschedule-start", slotA);
  await page.getByTestId("reschedule-submit").click();
  await expect(page.getByTestId("overlap-dialog")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("overlap-dialog")).toContainText(`A${RUN}`);
  await page.getByTestId("overlap-confirm").click();
  await expectToast(page, "نوبت جابه‌جا شد");

  // Cancel B.
  await (await findAppointmentRow(page, `B${RUN}`)).getByTestId("appointment-open").click();
  await page.getByTestId("appointment-cancel").click();
  await page.getByTestId("cancel-reason").fill("synthetic cancel");
  await page.getByTestId("cancel-confirm").click();
  await expectToast(page, "نوبت لغو شد");
  await page.getByTestId("filter-status").selectOption("CANCELLED");
  await findAppointmentRow(page, `B${RUN}`);

  // Patient-to-appointment navigation: patient profile history links back to the calendar.
  await page.getByTestId("filter-status").selectOption("");
  await (await findAppointmentRow(page, `A${RUN}`)).getByTestId("appointment-open").click();
  await page.getByTestId("appointment-patient-link").click();
  await expect(page.getByTestId("patient-profile-page")).toBeVisible();
  await expect(page.getByTestId("patient-history-row")).toHaveCount(1);
  await page.getByTestId("history-calendar-link").click();
  await expect(page.getByTestId("appointments-page")).toBeVisible();
  await findAppointmentRow(page, `A${RUN}`);
});

test("manager: dashboard shows real counts and patients search finds authorized records", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await gotoNav(page, "داشبورد", "dashboard-page");
  for (const id of ["dashboard-count", "dashboard-patients", "dashboard-staff"]) {
    await expect(page.getByTestId(id)).toHaveText(/^\d+$/, { timeout: 30_000 });
  }
  expect(Number(await page.getByTestId("dashboard-count").innerText())).toBeGreaterThanOrEqual(2);
  expect(Number(await page.getByTestId("dashboard-patients").innerText())).toBeGreaterThanOrEqual(2);

  // Top-bar global search removed (UX-04); patients workspace search is the authorized finder.
  await gotoNav(page, "بیماران", "patients-page");
  await page.getByTestId("patients-search-query").fill(`A${RUN}`);
  await page.getByTestId("patients-search-submit").click();
  const row = page.getByTestId("patients-result-row").filter({ hasText: `A${RUN}` });
  await expect(row.first()).toBeVisible({ timeout: 15_000 });
  await row.first().getByTestId("patients-open-profile").click();
  await expect(page.getByTestId("patient-profile-page")).toBeVisible({ timeout: 20_000 });

  const summary = await bff(page, "GET", `/api/v1/search?q=${encodeURIComponent(`A${RUN}`)}`);
  expect(summary.status).toBe(200);
  await assertNoNonLatinDigits(page);
});
