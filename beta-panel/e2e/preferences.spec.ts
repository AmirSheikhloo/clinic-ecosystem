/** Browser-local preferences: applied before hydration, persisted, non-sensitive, never server state. */
import { expect, test, type Page } from "@playwright/test";
import { credsFromEnv, loginAs } from "./ops-helpers";

const KEYS = ["ce_beta_theme_pref", "ce_beta_appearance_pref", "ce_beta_density_pref", "ce_beta_sidebar_pref", "ce_beta_motion_pref"];

async function root(page: Page) {
  return page.evaluate(() => {
    const el = document.documentElement;
    return { theme: el.dataset.theme, appearance: el.dataset.appearance, density: el.dataset.density, sidebar: el.dataset.sidebar, motion: el.dataset.motion };
  });
}

test.describe.configure({ mode: "serial" });

test("preferences change the document, persist across reload and reset to defaults", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/preferences");
  await expect(page.getByTestId("preferences-page")).toBeVisible();
  await expect(page.getByTestId("preferences-scope")).toContainText("همین مرورگر");

  await page.getByTestId("pref-appearance-dark").click();
  await page.getByTestId("pref-density-compact").click();
  await page.getByTestId("pref-sidebar-collapsed").click();
  await page.getByTestId("pref-motion-reduced").click();
  await page.getByTestId("pref-theme").getByRole("radio").nth(1).click();

  const changed = await root(page);
  expect(changed).toMatchObject({ appearance: "dark", density: "compact", sidebar: "collapsed", motion: "reduced" });
  expect(changed.theme).not.toBe("ocean");

  await page.reload();
  await expect(page.getByTestId("preferences-page")).toBeVisible();
  expect(await root(page)).toEqual(changed);

  const stored = await page.evaluate((keys) => Object.fromEntries(keys.map((key) => [key, localStorage.getItem(key)])), KEYS);
  for (const value of Object.values(stored)) expect(value).toMatch(/^[a-z-]+$/);

  const everything = await page.evaluate(() => JSON.stringify({ ...localStorage }));
  expect(everything).not.toMatch(/token|csrf|session|patient|password/i);

  await page.getByTestId("preferences-reset").click();
  expect(await root(page)).toMatchObject({ theme: "ocean", appearance: "light", density: "comfortable", sidebar: "expanded", motion: "system" });
});

test("compact density changes row height and reduced motion removes transitions", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/preferences");
  const height = () =>
    page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--ds-control-height")));
  await page.getByTestId("pref-density-comfortable").click();
  const comfortable = await height();
  await page.getByTestId("pref-density-compact").click();
  const compact = await height();
  expect(compact).toBeLessThan(comfortable);

  await page.getByTestId("pref-motion-reduced").click();
  const duration = await page.evaluate(() => getComputedStyle(document.querySelector("button")!).transitionDuration);
  expect(duration.split(",").every((value) => parseFloat(value) <= 0.01)).toBe(true);
  await page.getByTestId("preferences-reset").click();
});
