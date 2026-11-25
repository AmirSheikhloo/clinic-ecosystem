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
  await expect(page).toHaveURL(/\/desk/, { timeout: 45_000 });
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
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
