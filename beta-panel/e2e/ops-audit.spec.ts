/**
 * Management audit workspace: list + filter over append-only audit_entries.
 */
import { expect, test } from "@playwright/test";
import { assertNoNonLatinDigits } from "./helpers";
import { bff, credsFromEnv, gotoNav, loginAs } from "./ops-helpers";

test.describe.configure({ mode: "serial" });

test("manager: audit nav, list, filter, pagination marker", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await gotoNav(page, "حسابرسی", "audit-page");
  await expect(page.getByTestId("audit-row").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("audit-total")).toBeVisible();
  const totalText = await page.getByTestId("audit-total").innerText();
  expect(totalText.length).toBeGreaterThan(5);

  await page.getByTestId("audit-target-filter").selectOption("appointment");
  await expect(page.getByTestId("audit-row").first()).toBeVisible({ timeout: 30_000 });
  await assertNoNonLatinDigits(page);

  const api = await bff(page, "GET", "/api/v1/audit/entries?limit=5&offset=0&target_type=appointment");
  expect(api.status).toBe(200);
  const body = api.body as { items?: unknown[]; total?: number };
  expect(Array.isArray(body.items)).toBe(true);
  expect((body.total ?? 0) > 0).toBe(true);
});

test("owner: audit entries readable; details contain no ciphertext keys", async ({ page }) => {
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  const api = await bff(page, "GET", "/api/v1/audit/entries?limit=20");
  expect(api.status).toBe(200);
  const body = api.body as { items: Array<{ details: Record<string, unknown> }> };
  for (const item of body.items) {
    const blob = JSON.stringify(item.details);
    expect(blob).not.toMatch(/ciphertext|nonce_96|auth_tag|password_hash/i);
  }
});
