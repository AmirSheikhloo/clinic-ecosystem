/**
 * Jalali controls, keyboard-first reception, responsive navigation and breadcrumbs
 * against the real BFF + API + PG15. Synthetic data only.
 */
import { expect, test } from "@playwright/test";
import { jalaliParts } from "../lib/calendar/jalali-grid";
import { formatJalaliInput } from "../lib/calendar/jalali-input";
import { tehranTodayYmd } from "../lib/tehran";
import { assertNoNonLatinDigits, navLink } from "./helpers";
import { fillJalaliDateTime } from "./jalali-helpers";
import {
  RUN,
  bff,
  credsFromEnv,
  deskBook,
  deskRegisterPatient,
  loginAs,
  pickComboboxOption,
  tehranSlot,
} from "./ops-helpers";

test.describe.configure({ mode: "serial" });

test("Jalali date control: typed input, Persian digits, calendar popover and Escape focus return", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  // Birth-date field is on stage 1; appointment-start only mounts after a patient is selected.
  const today = tehranTodayYmd();
  const dateInput = page.getByTestId("patient-birth-date");
  await page.getByTestId("patient-birth-date-open").click();
  const popover = page.getByTestId("patient-birth-date-popover");
  await expect(popover).toBeVisible();
  await page.getByTestId(`patient-birth-date-day-${today}`).click();
  await expect(popover).toBeHidden();
  await expect(dateInput).toHaveValue(formatJalaliInput(today));
  await expect(dateInput).toBeFocused();
  expect(await dateInput.inputValue()).toMatch(/^\d{4}\/\d{2}\/\d{2}$/);

  const { jy } = jalaliParts(today);
  await dateInput.fill(`${String(jy).replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[Number(d)])}/۰۱/۰۱`);
  await expect(dateInput).toHaveValue(`${jy}/01/01`);

  await page.getByTestId("patient-birth-date-open").click();
  await expect(popover).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(popover).toBeHidden();
  await expect(dateInput).toBeFocused();
  await assertNoNonLatinDigits(page);
});

test("reception: keyboard patient search, selection, booking, then next-patient reset", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  const last = `Key${RUN}`;
  const created = await bff(page, "POST", "/api/patients", { body: { first_name: "UxPat", last_name: last } });
  expect(created.status).toBe(201);

  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("patient-search-query").fill(last);
  await expect(page.getByTestId("patient-result")).toHaveCount(1, { timeout: 15_000 });
  await page.getByTestId("patient-search-query").press("ArrowDown");
  await page.getByTestId("patient-search-query").press("Enter");
  // Stage advances to booking; patient identity is mirrored in the summary/cashier.
  await expect(
    page
      .getByTestId("summary-patient")
      .or(page.getByTestId("invoice-patient"))
      .or(page.getByTestId("selected-patient"))
      .filter({ hasText: `UxPat ${last}` })
      .first(),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("appointment-submit")).toBeDisabled();
  await expect(page.getByTestId("booking-missing")).toContainText("انتخاب خدمت");

  await deskBook(page, tehranSlot(5, 14));
  await expect(page.getByTestId("desk-status")).toContainText("نوبت ثبت شد", { timeout: 45_000 });
  await expect(page.getByTestId("desk-open-calendar")).toBeVisible();

  await page.getByTestId("desk-next-patient").first().click();
  await expect(page.getByTestId("desk-stage-patient")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("patient-search-query")).toBeFocused();
  await expect(page.getByTestId("desk-status")).toHaveCount(0);
  await assertNoNonLatinDigits(page);
});

test("desk shows required resources clearly and registers a patient with a Jalali birth date", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("patient-birth-date").fill("1370/05/15");
  await deskRegisterPatient(page, "UxBirth", `Jal${RUN}`);
  await expect(page.getByTestId("desk-stage-booking")).toBeVisible({ timeout: 15_000 });
  await pickComboboxOption(page, "service-select", process.env.BETA01B_SERVICE_NAME || "Tenant A Consultation");
  await expect(page.getByTestId("requirements-summary")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("requirements-summary")).toContainText("×");
  await expect(
    page
      .getByTestId("summary-patient")
      .or(page.getByTestId("invoice-patient"))
      .or(page.getByTestId("selected-patient"))
      .filter({ hasText: "UxBirth" })
      .first(),
  ).toBeVisible();
});

test("mobile navigation drawer opens, navigates and closes with Escape", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("app-sidebar")).toBeHidden();
  await page.getByTestId("mobile-nav-open").click();
  const drawer = page.getByTestId("mobile-nav");
  await expect(drawer).toBeVisible();
  await drawer.getByRole("link", { name: "بیماران", exact: true }).click();
  await expect(page.getByTestId("patients-page")).toBeVisible({ timeout: 30_000 });
  await expect(drawer).toBeHidden();

  await page.getByTestId("mobile-nav-open").click();
  await expect(drawer).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(page.getByTestId("mobile-nav-open")).toBeFocused();
});

test("collapsed sidebar rail keeps accessible names and shows tooltips; breadcrumbs reflect the page", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/appointments");
  await expect(page.getByTestId("appointments-page")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("breadcrumbs")).toContainText("مدیریت نوبت‌ها");

  await page.getByTestId("sidebar-toggle").click();
  await expect(page.getByTestId("sidebar-toggle")).toHaveAttribute("aria-expanded", "false");
  const link = navLink(page, "بیماران");
  await expect(link).toBeVisible();
  await link.hover();
  const tip = link.locator("xpath=following-sibling::span[contains(@class,'ds-tooltip')]");
  await expect(tip).toHaveText("بیماران");
  await expect(tip).toHaveCSS("opacity", "1");
  await page.getByTestId("sidebar-toggle").click();
  await expect(page.getByTestId("sidebar-toggle")).toHaveAttribute("aria-expanded", "true");
});
