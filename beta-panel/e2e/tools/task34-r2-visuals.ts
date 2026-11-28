/**
 * Multi-width visual capture for Task 34 R2.
 * Usage:
 *   BETA01B_E2E_ENV_FILE=... SHOT_DIR=/opt/cursor/artifacts/task34-r2-visuals \
 *   npx tsx e2e/tools/task34-r2-visuals.ts
 */
import { chromium, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

function unquote(value: string): string {
  if (
    (value.startsWith("'") && value.endsWith("'")) ||
    (value.startsWith('"') && value.endsWith('"'))
  ) {
    return value.slice(1, -1);
  }
  return value;
}

function loadEnv(file: string) {
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const idx = line.indexOf("=");
    const key = line.slice(0, idx);
    const value = unquote(line.slice(idx + 1));
    if (!process.env[key]) process.env[key] = value;
  }
}

const WIDTHS = [375, 768, 1280, 1440] as const;
const PAGES: Array<{ name: string; path: string; ready: string }> = [
  { name: "dashboard", path: "/dashboard", ready: "dashboard-page" },
  { name: "reception-desk", path: "/desk", ready: "desk-page" },
  { name: "appointments-calendar", path: "/appointments", ready: "appointments-page" },
];

async function login(page: Page) {
  await page.goto("/login");
  await page.evaluate(async () => {
    await fetch("/api/auth/csrf", { method: "GET", credentials: "same-origin" });
  });
  await page.waitForTimeout(300);
  const demo = page.getByTestId("demo-role-receptionist");
  if (await demo.isVisible().catch(() => false)) {
    await demo.click();
  } else {
    await page.getByTestId("login-identifier").fill(process.env.BETA01B_RECEPTIONIST_LOGIN || "receptionist");
    await page
      .getByTestId("login-password")
      .fill(process.env.BETA01B_RECEPTIONIST_PASSWORD || "Clinic123!");
    await page.getByTestId("login-submit").click();
  }
  await page.waitForURL(/\/(dashboard|desk)/, { timeout: 45_000 });
}

async function main() {
  const envFile = process.env.BETA01B_E2E_ENV_FILE;
  if (envFile) loadEnv(envFile);
  const base = process.env.BETA01B_PANEL_BASE_URL;
  if (!base) throw new Error("BETA01B_PANEL_BASE_URL required");
  const out = process.env.SHOT_DIR || "/opt/cursor/artifacts/task34-r2-visuals";
  fs.mkdirSync(out, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    locale: "fa-IR",
    baseURL: base,
  });
  const page = await context.newPage();
  await login(page);

  const manifest: Array<{ file: string; width: number; route: string }> = [];
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: width <= 768 ? 844 : 900 });
    for (const route of PAGES) {
      await page.goto(route.path, { waitUntil: "networkidle" });
      await page.getByTestId(route.ready).waitFor({ timeout: 45_000 });
      await page.waitForTimeout(500);
      const file = `${route.name}-${width}.png`;
      const full = path.join(out, file);
      await page.screenshot({ path: full, fullPage: true });
      manifest.push({ file, width, route: route.path });
      console.log("SHOT", full);
    }
  }

  fs.writeFileSync(path.join(out, "manifest.json"), JSON.stringify({ base, manifest }, null, 2) + "\n");
  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
