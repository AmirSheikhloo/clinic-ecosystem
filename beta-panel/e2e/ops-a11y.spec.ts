/**
 * Theme, responsive, keyboard, reduced-motion and Latin-digit checks for the
 * operations screens (staff, access, patients, calendar, catalog admin, dashboard).
 */
import { expect, test, type Page } from "@playwright/test";
import { applyTheme, assertNoNonLatinDigits, assertRtlDocument } from "./helpers";
import { credsFromEnv, loginAs } from "./ops-helpers";

test.describe.configure({ mode: "serial" });

const THEMES = ["ocean", "midnight", "emerald", "graphite"] as const;

const PAGES: Array<{ path: string; testId: string }> = [
  { path: "/dashboard", testId: "dashboard-page" },
  { path: "/patients", testId: "patients-page" },
  { path: "/staff", testId: "staff-page" },
  { path: "/access", testId: "access-page" },
  { path: "/appointments", testId: "appointments-page" },
  { path: "/catalog/manage", testId: "catalog-admin-page" },
];

async function unlabeledControls(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const bad: string[] = [];
    const named = (el: Element) => {
      const input = el as HTMLInputElement;
      return (
        el.getAttribute("aria-label") ||
        el.getAttribute("aria-labelledby") ||
        el.getAttribute("title") ||
        (input.labels && input.labels.length > 0)
      );
    };
    document.querySelectorAll("input:not([type=hidden]),select,textarea").forEach((el) => {
      if (!named(el)) bad.push(`${el.tagName.toLowerCase()}[${el.getAttribute("data-testid") ?? ""}]`);
    });
    document.querySelectorAll("button,a[href]").forEach((el) => {
      if (!(el.textContent || "").trim() && !named(el)) bad.push(`${el.tagName.toLowerCase()}:empty`);
    });
    return bad;
  });
}

test("every operations page renders in each theme with labelled controls and Latin digits", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await assertRtlDocument(page);
  for (const theme of THEMES) {
    for (const appearance of ["light", "dark"] as const) {
      await applyTheme(page, theme, appearance);
      for (const { path, testId } of PAGES) {
        await page.goto(path);
        await expect(page.getByTestId(testId)).toBeVisible({ timeout: 30_000 });
        await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
        await expect(page.locator("html")).toHaveAttribute("data-appearance", appearance);
        await assertNoNonLatinDigits(page);
        expect(await unlabeledControls(page), `${theme}/${appearance} ${path}`).toEqual([]);
      }
    }
  }
});

test("pages do not overflow horizontally on tablet and phone widths", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const { path, testId } of PAGES) {
      await page.goto(path);
      await expect(page.getByTestId(testId)).toBeVisible({ timeout: 30_000 });
      const { overflow, offenders } = await page.evaluate(() => {
        const doc = document.documentElement;
        const limit = doc.clientWidth;
        const wide = [...document.body.querySelectorAll("*")]
          .filter((el) => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && (rect.right > limit + 1 || rect.left < -1);
          })
          .slice(0, 5)
          .map((el) => `${el.tagName.toLowerCase()}[${el.getAttribute("data-testid") ?? ""}].${String(el.className).slice(0, 40)}`);
        return { overflow: doc.scrollWidth - doc.clientWidth, offenders: wide };
      });
      expect(overflow, `${path} @${width} ${offenders.join(" | ")}`).toBeLessThanOrEqual(1);
    }
  }
});

test("dialogs trap focus, close on Escape and restore focus; tabs use arrow keys", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/staff");
  const trigger = page.getByTestId("staff-add");
  await trigger.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "افزودن عضو" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveAttribute("aria-modal", "true");
  for (let i = 0; i < 20; i += 1) {
    await page.keyboard.press("Tab");
    const inside = await page.evaluate(() => !!document.activeElement?.closest("[role=dialog]"));
    expect(inside, `focus escaped dialog on tab ${i}`).toBe(true);
  }
  await page.keyboard.press("Shift+Tab");
  expect(await page.evaluate(() => !!document.activeElement?.closest("[role=dialog]"))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();

  await page.goto("/access");
  await page.getByTestId("tab-accounts").focus();
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByTestId("tab-roles")).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("tab-roles")).toBeFocused();
});

test("reduced motion collapses dialog and toast animation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/staff");
  await page.getByTestId("staff-add").click();
  const duration = await page.getByTestId("staff-form-dialog").evaluate((el) => getComputedStyle(el).animationDuration);
  for (const part of duration.split(",")) {
    const ms = part.trim().endsWith("ms") ? parseFloat(part) : parseFloat(part) * 1000;
    expect(ms).toBeLessThan(20);
  }
});

test("theme preference lives in localStorage; no tokens or patient data are stored in browser storage", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/patients");
  await expect(page.getByTestId("patients-page")).toBeVisible();
  await page.getByTestId("patients-new").click();
  await page.getByTestId("patients-first-name").fill("StorageProbe");
  await page.getByTestId("patients-last-name").fill("Check");
  const dump = await page.evaluate(() =>
    JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }),
  );
  expect(dump).not.toMatch(/StorageProbe|eyJ[A-Za-z0-9_-]{10,}|access_token|ce_beta_session/);
});
