import { expect, type Page } from "@playwright/test";

const SESSION = "ce_beta_session";
const CSRF = "ce_beta_csrf";

export const loginId = () => process.env.BETA01B_RECEPTIONIST_LOGIN || "";
export const password = () => process.env.BETA01B_RECEPTIONIST_PASSWORD || "";

export function requireCreds() {
  if (!loginId() || !password()) {
    throw new Error("Missing receptionist credentials for browser E2E");
  }
}

/** Persian/Arabic-Indic digits must never appear in rendered UI text. */
export const NON_LATIN_DIGIT_RE = /[\u0660-\u0669\u06F0-\u06F9]/;

export async function assertHttpOnlySession(page: Page) {
  const cookies = await page.context().cookies();
  const session = cookies.find((c) => c.name === SESSION);
  expect(session, "HttpOnly session cookie must exist").toBeTruthy();
  expect(session!.httpOnly).toBe(true);
  expect(session!.value.length).toBeGreaterThan(20);
  const jsCookies = await page.evaluate(() => document.cookie);
  expect(jsCookies.includes(SESSION)).toBe(false);
  expect(jsCookies.includes(session!.value)).toBe(false);
}

export async function loginAsReceptionist(page: Page) {
  requireCreds();
  await page.goto("/login");
  await page.evaluate(async () => {
    await fetch("/api/auth/csrf", { method: "GET", credentials: "same-origin" });
  });
  await expect
    .poll(async () => {
      const cookies = await page.context().cookies();
      return cookies.some((c) => c.name === CSRF && c.value.length > 0);
    })
    .toBe(true);
  await page.getByTestId("login-identifier").fill(loginId());
  await page.getByTestId("login-password").fill(password());
  await page.getByTestId("login-submit").click();
  // Login lands on dashboard (Task 34 R2); older builds redirected to /desk.
  await expect(page).toHaveURL(/\/(dashboard|desk)/, { timeout: 45_000 });
  await expect(page.getByTestId("app-sidebar").or(page.getByTestId("desk-page"))).toBeVisible({
    timeout: 45_000,
  });
  await assertHttpOnlySession(page);
}

export async function assertNoNonLatinDigits(page: Page) {
  const text = await page.locator("body").innerText();
  expect(text).not.toMatch(NON_LATIN_DIGIT_RE);
}

export async function assertRtlDocument(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "fa");
}

/** Opens the theme menu when needed, applies palette and (optionally) appearance, then closes it. */
export async function applyTheme(page: Page, theme: string, appearance?: "light" | "dark") {
  const select = page.getByTestId("theme-select");
  if (!(await select.isVisible())) await page.getByTestId("theme-menu-button").click();
  await select.selectOption(theme);
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  if (appearance) {
    const current = await page.locator("html").getAttribute("data-appearance");
    if (current !== appearance) await page.getByTestId("appearance-toggle").click();
    await expect(page.locator("html")).toHaveAttribute("data-appearance", appearance);
  }
  await page.keyboard.press("Escape");
  await expect(select).toBeHidden();
}

/** Main navigation link by its exact accessible name (avoids matching in-page links). */
export function navLink(page: Page, name: string) {
  return page.getByRole("navigation", { name: "ناوبری اصلی" }).getByRole("link", { name, exact: true });
}
