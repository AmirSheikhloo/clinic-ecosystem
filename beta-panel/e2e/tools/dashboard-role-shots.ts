import { chromium } from "@playwright/test";
import fs from "node:fs";
function loadEnv(file: string) {
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const i = line.indexOf("=");
    if (i > 0 && !process.env[line.slice(0, i)]) process.env[line.slice(0, i)] = line.slice(i + 1);
  }
}
async function shot(label: string, login: string, password: string, out: string) {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "fa-IR", baseURL: process.env.BETA01B_PANEL_BASE_URL });
  const page = await context.newPage();
  await page.goto("/login");
  await page.evaluate(() => fetch("/api/auth/csrf", { credentials: "same-origin" }));
  await page.waitForTimeout(250);
  await page.getByTestId("login-identifier").fill(login);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/(desk|dashboard)/, { timeout: 45_000 });
  await page.goto("/dashboard");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/${label}.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${out}/${label}-mobile.png`, fullPage: true });
  await browser.close();
  console.log("ok", label);
}
async function main() {
  loadEnv(process.env.BETA01B_E2E_ENV_FILE!);
  const out = process.env.SHOT_DIR!;
  fs.mkdirSync(out, { recursive: true });
  await shot("receptionist", process.env.BETA01B_RECEPTIONIST_LOGIN!, process.env.BETA01B_RECEPTIONIST_PASSWORD!, out);
  await shot("manager", process.env.BETA02_MANAGER_LOGIN!, process.env.BETA02_MANAGER_PASSWORD!, out);
  await shot("owner", process.env.BETA02_OWNER_LOGIN!, process.env.BETA02_OWNER_PASSWORD!, out);
  await shot("deputy", process.env.BETA02_DEPUTY_LOGIN!, process.env.BETA02_DEPUTY_PASSWORD!, out);
}
main().catch((e) => { console.error(e); process.exit(1); });
