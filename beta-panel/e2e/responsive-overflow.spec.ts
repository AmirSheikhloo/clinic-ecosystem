/** No workspace scrolls the whole page sideways at phone, tablet and small-laptop widths, in any theme. */
import { expect, test } from "@playwright/test";
import { credsFromEnv, loginAs } from "./ops-helpers";

const PATHS = ["/dashboard", "/desk", "/appointments", "/patients", "/catalog", "/catalog/manage", "/staff", "/access", "/preferences"];
const WIDTHS = [390, 768, 1024];

test.describe.configure({ mode: "serial" });

test("pages never overflow the viewport horizontally", async ({ page }) => {
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of PATHS) {
      await page.goto(path);
      await expect(page.locator("main").first()).toBeVisible({ timeout: 30_000 });
      await page.waitForTimeout(400);
      const overflow = await page.evaluate(() => {
        const root = document.documentElement;
        const offenders = Array.from(document.querySelectorAll<HTMLElement>("main *"))
          .filter((node) => node.getBoundingClientRect().right > window.innerWidth + 1 && !node.closest(".overflow-x-auto, .ds-table-wrap, .ds-week-scroll, .ds-day-scroll, [data-scroll]"))
          .slice(0, 3)
          .map((node) => `${node.tagName.toLowerCase()}.${String(node.className).slice(0, 40)}`);
        return { scroll: root.scrollWidth - window.innerWidth, offenders };
      });
      expect(overflow.scroll, `${path} @${width}: horizontal page scroll (${overflow.offenders.join(", ")})`).toBeLessThanOrEqual(1);
    }
  }
});

test("calendar week and month stay reachable on a phone by scrolling their own frame", async ({ page }) => {
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/appointments?view=week");
  await expect(page.getByTestId("week-view")).toBeVisible({ timeout: 30_000 });
  const week = await page.getByTestId("week-view").evaluate((node) => ({ scrollable: node.scrollWidth > node.clientWidth, page: document.documentElement.scrollWidth - window.innerWidth }));
  expect(week.scrollable).toBe(true);
  expect(week.page).toBeLessThanOrEqual(1);
  await page.goto("/appointments?view=month");
  await expect(page.getByTestId("month-view")).toBeVisible({ timeout: 30_000 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1);
});
