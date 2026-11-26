/**
 * Capture primary workspaces at 1280 / 1440 / 1920 / mobile widths.
 * Usage: BETA01B_E2E_ENV_FILE=... SHOT_DIR=... npx tsx e2e/tools/capture-multi-width.ts
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";

function loadEnv(file: string) {
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const idx = line.indexOf("=");
    if (idx <= 0) continue;
    const key = line.slice(0, idx);
    let value = line.slice(idx + 1);
    if ((value.startsWith("'") && value.endsWith("'")) || (value.startsWith('"') && value.endsWith('"'))) {
      value = value.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = value;
  }
}

const WIDTHS = [
  { name: "w1280", width: 1280, height: 900 },
  { name: "w1440", width: 1440, height: 900 },
  { name: "w1920", width: 1920, height: 1080 },
  { name: "mobile", width: 390, height: 844 },
] as const;

const PAGES = [
  ["dashboard", "/dashboard", "dashboard-page"],
  ["desk", "/desk", "desk-page"],
  ["appointments", "/appointments", "appointments-page"],
  ["patients", "/patients", "patients-page"],
  ["audit", "/audit", "audit-page"],
] as const;

async function main() {
  if (process.env.BETA01B_E2E_ENV_FILE) loadEnv(process.env.BETA01B_E2E_ENV_FILE);
  const base = process.env.BETA01B_PANEL_BASE_URL!;
  const out = process.env.SHOT_DIR || "/opt/cursor/artifacts/task32-screens";
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();

  for (const vp of WIDTHS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      locale: "fa-IR",
      baseURL: base,
    });
    const page = await context.newPage();
    await page.goto("/login");
    await page.evaluate(() => fetch("/api/auth/csrf", { credentials: "same-origin" }));
    await page.waitForTimeout(200);
    await page.getByTestId("login-identifier").fill(process.env.BETA02_OWNER_LOGIN!);
    await page.getByTestId("login-password").fill(process.env.BETA02_OWNER_PASSWORD!);
    await page.getByTestId("login-submit").click();
    await page.waitForURL(/\/(desk|dashboard)/, { timeout: 45_000 });

    for (const [slug, href, marker] of PAGES) {
      await page.goto(href);
      await page.getByTestId(marker).waitFor({ timeout: 45_000 });
      await page.waitForTimeout(400);
      const path = `${out}/${vp.name}-${slug}.png`;
      await page.screenshot({ path, fullPage: true });
      console.log(path);
    }
    await context.close();
  }
  await browser.close();
}

void main();
