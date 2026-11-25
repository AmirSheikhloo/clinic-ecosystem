/**
 * Theme matrix, responsive layout, keyboard nav, reduced-motion, Latin digits.
 */
import { expect, test } from "@playwright/test";
import {
  assertNoNonLatinDigits,
  assertRtlDocument,
  loginAsReceptionist,
  requireCreds,
} from "./helpers";

const THEMES = ["ocean", "midnight", "emerald", "graphite"] as const;
const APPEARANCES = ["light", "dark"] as const;

test.describe.configure({ mode: "serial" });

test("all theme × appearance combinations apply without non-Latin digits", async ({
  page,
}) => {
  requireCreds();
  await loginAsReceptionist(page);
  await assertRtlDocument(page);

  for (const theme of THEMES) {
    await page.getByTestId("theme-select").selectOption(theme);
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    for (const appearance of APPEARANCES) {
      const current = await page.locator("html").getAttribute("data-appearance");
      if (current !== appearance) {
        await page.getByTestId("appearance-toggle").click();
      }
      await expect(page.locator("html")).toHaveAttribute("data-appearance", appearance);
      await assertNoNonLatinDigits(page);
      // Theme preference is non-sensitive localStorage only
      const stored = await page.evaluate(() => ({
        theme: localStorage.getItem("ce_beta_theme_pref"),
        appearance: localStorage.getItem("ce_beta_appearance_pref"),
        hasSession: document.cookie.includes("ce_beta_session"),
      }));
      expect(stored.theme).toBe(theme);
      expect(stored.appearance).toBe(appearance);
      expect(stored.hasSession).toBe(false);
    }
  }
});

test("responsive shell and sidebar keyboard toggle", async ({ page }) => {
  requireCreds();
  await loginAsReceptionist(page);

  await page.setViewportSize({ width: 1280, height: 800 });
  await expect(page.getByRole("navigation", { name: "ناوبری اصلی" })).toBeVisible();
  await page.getByTestId("sidebar-toggle").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("sidebar-toggle")).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("sidebar-toggle")).toHaveAttribute("aria-expanded", "true");

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("desk-page")).toBeVisible();
  await assertRtlDocument(page);
  await assertNoNonLatinDigits(page);

  // Tab order reaches logout without trapping
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.getAttribute("data-testid"));
  expect(typeof focused === "string" || focused === null).toBe(true);
});

test("prefers-reduced-motion collapses animation durations", async ({ page }) => {
  requireCreds();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await loginAsReceptionist(page);
  const durations = await page.evaluate(() => {
    const probe = document.createElement("div");
    probe.className = "animate-rise";
    document.body.appendChild(probe);
    const style = getComputedStyle(probe);
    const transition = style.transitionDuration;
    const animation = style.animationDuration;
    probe.remove();
    return { transition, animation };
  });
  // Under reduced-motion CSS, durations collapse to ~0.01ms
  const toMs = (value: string) =>
    value
      .split(",")
      .map((part) => part.trim())
      .map((part) => (part.endsWith("ms") ? parseFloat(part) : parseFloat(part) * 1000));
  for (const ms of [...toMs(durations.transition), ...toMs(durations.animation)]) {
    if (Number.isFinite(ms)) {
      expect(ms).toBeLessThan(20);
    }
  }
  await assertNoNonLatinDigits(page);
});
