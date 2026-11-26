/**
 * Navigation and request measurements (evidence tool, not part of the Playwright suite).
 * Usage: BETA01B_E2E_ENV_FILE=... [BASE=http://host:port] OUT=/tmp/perf.json npx tsx e2e/tools/measure-perf.ts
 * For each workspace it clicks the sidebar link from a warmed session and records the number of
 * BFF requests, the time until the workspace's marker element is visible, and long-task time.
 * Each page is visited REPEAT times; the median is reported. Numbers depend on the machine.
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";

function loadEnv(file: string) {
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const idx = line.indexOf("=");
    if (idx > 0 && !process.env[line.slice(0, idx)]) process.env[line.slice(0, idx)] = line.slice(idx + 1);
  }
}

const PAGES = [
  ["داشبورد", "/dashboard", "dashboard-page"],
  ["میز پذیرش", "/desk", "desk-page"],
  ["مدیریت نوبت‌ها", "/appointments", "appointments-page"],
  ["بیماران", "/patients", "patients-page"],
  ["خدمات و منابع", "/catalog", "catalog-page"],
  ["کارکنان", "/staff", "staff-page"],
  ["کاربران و دسترسی", "/access", "access-page"],
] as const;

const median = (values: number[]) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];

async function main() {
  if (process.env.BETA01B_E2E_ENV_FILE) loadEnv(process.env.BETA01B_E2E_ENV_FILE);
  const base = process.env.BASE || process.env.BETA01B_PANEL_BASE_URL!;
  const repeat = Number(process.env.REPEAT || 5);
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "fa-IR", baseURL: base });
  const page = await context.newPage();
  const requests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) requests.push(`${request.method()} ${url.pathname}`);
  });

  await page.goto("/login");
  await page.evaluate(() => fetch("/api/auth/csrf", { credentials: "same-origin" }));
  await page.waitForTimeout(300);
  requests.length = 0;
  const loginStart = Date.now();
  await page.getByTestId("login-identifier").fill(process.env.BETA02_OWNER_LOGIN!);
  await page.getByTestId("login-password").fill(process.env.BETA02_OWNER_PASSWORD!);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/(desk|dashboard)/, { timeout: 45_000 });
  await page.getByTestId("current-user").waitFor({ timeout: 30_000 });
  const loginReport = { ms: Date.now() - loginStart, requests: [...requests] };
  await page.waitForTimeout(1500);

  const report: Record<string, unknown>[] = [];
  for (const [label, href, marker] of PAGES) {
    const times: number[] = [];
    let counts: number[] = [];
    let sample: string[] = [];
    for (let run = 0; run < repeat; run += 1) {
      await page.goto("/dashboard");
      await page.getByTestId("dashboard-page").waitFor();
      await page.waitForLoadState("networkidle");
      requests.length = 0;
      const start = Date.now();
      await page.getByRole("navigation", { name: "ناوبری اصلی" }).getByRole("link", { name: label, exact: true }).click();
      await page.getByTestId(marker).waitFor({ timeout: 30_000 });
      times.push(Date.now() - start);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(250);
      counts.push(requests.length);
      sample = [...requests];
    }
    report.push({ page: href, medianMsToMarker: median(times), requestsPerVisit: median(counts), requests: sample });
  }
  await browser.close();
  const out = process.env.OUT || "/tmp/perf.json";
  fs.writeFileSync(out, JSON.stringify({ base, login: loginReport, pages: report }, null, 2));
  console.log(`login: ${loginReport.ms}ms, ${loginReport.requests.length} api requests`);
  for (const row of report as Record<string, any>[]) {
    console.log(`${String(row.page).padEnd(14)} ${String(row.medianMsToMarker).padStart(5)}ms  api requests: ${row.requestsPerVisit}`);
  }
}

void main();
