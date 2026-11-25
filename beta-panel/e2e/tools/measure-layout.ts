/**
 * Layout-stability measurement for the Product Owner report (not part of the Playwright suite).
 * Usage: BETA01B_E2E_ENV_FILE=... OUT=/tmp/geometry.json npx tsx e2e/tools/measure-layout.ts
 * Navigates every workspace by clicking the sidebar (client-side navigation) with real scrollbars
 * (headless Chromium hides them by default) and records settled deltas, per-frame deviation,
 * layout-shift entries, and the document scrollbar width on each page.
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import {
  maxFrameDeviation,
  rectDeltas,
  shellRects,
  startSampling,
  stopSampling,
  type ShellRects,
} from "../layout-geometry";

function loadEnv(file: string) {
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const idx = line.indexOf("=");
    if (idx > 0 && !process.env[line.slice(0, idx)]) process.env[line.slice(0, idx)] = line.slice(idx + 1);
  }
}

const PAGES = [
  ["داشبورد", "/dashboard"],
  ["میز پذیرش", "/desk"],
  ["تقویم نوبت‌ها", "/appointments"],
  ["بیماران", "/patients"],
  ["خدمات و منابع", "/catalog"],
  ["کارکنان", "/staff"],
  ["کاربران و دسترسی", "/access"],
] as const;

async function main() {
  if (process.env.BETA01B_E2E_ENV_FILE) loadEnv(process.env.BETA01B_E2E_ENV_FILE);
  const base = process.env.BETA01B_PANEL_BASE_URL!;
  const widths = (process.env.WIDTHS || "1280,1440,1920").split(",").map(Number);
  const browser = await chromium.launch({ ignoreDefaultArgs: ["--hide-scrollbars"] });
  const report: Record<string, unknown>[] = [];
  for (const width of widths) {
    const context = await browser.newContext({ viewport: { width, height: 800 }, locale: "fa-IR", baseURL: base });
    const page = await context.newPage();
    await page.goto("/login");
    await page.evaluate(() => fetch("/api/auth/csrf", { credentials: "same-origin" }));
    await page.waitForTimeout(300);
    await page.getByTestId("login-identifier").fill(process.env.BETA02_OWNER_LOGIN!);
    await page.getByTestId("login-password").fill(process.env.BETA02_OWNER_PASSWORD!);
    await page.getByTestId("login-submit").click();
    await page.waitForURL(/\/(desk|dashboard)/, { timeout: 45_000 });
    await page.waitForTimeout(1500);
    let reference: ShellRects | null = null;
    for (const [label, href] of PAGES) {
      await startSampling(page);
      await page.getByRole("navigation", { name: "ناوبری اصلی" }).getByRole("link", { name: label, exact: true }).click();
      await page.waitForURL(`**${href}`);
      await page.waitForTimeout(1800);
      const samples = await stopSampling(page);
      const settled = await shellRects(page);
      reference ??= settled;
      const scroll = await page.evaluate(() => ({
        scrollbar: window.innerWidth - document.documentElement.clientWidth,
        docHeight: document.documentElement.scrollHeight,
      }));
      report.push({
        width,
        page: href,
        scrollbarWidth: scroll.scrollbar,
        hasVerticalScroll: scroll.docHeight > 800,
        settledDeltaVsFirstPage: rectDeltas(reference, settled),
        maxFrameDeviation: maxFrameDeviation(samples),
        layoutShiftEntries: samples.shifts,
        layoutShiftValue: Number(samples.shiftValue.toFixed(4)),
        topbar: settled.topbar,
        search: settled.search,
        account: settled.account,
        frame: settled.frame,
      });
    }
    await context.close();
  }
  await browser.close();
  const out = process.env.OUT || "/tmp/geometry.json";
  fs.writeFileSync(out, JSON.stringify(report, null, 2));
  for (const row of report as Record<string, any>[]) {
    const d = row.settledDeltaVsFirstPage;
    console.log(
      `${row.width} ${String(row.page).padEnd(14)} sb=${row.scrollbarWidth} ` +
        `search(x=${row.search?.x.toFixed(1)} w=${row.search?.width.toFixed(1)}) ` +
        `account(x=${row.account?.x.toFixed(1)} w=${row.account?.width.toFixed(1)}) ` +
        `frame(x=${row.frame?.x.toFixed(1)} w=${row.frame?.width.toFixed(1)}) ` +
        `Δsearch=${d.search?.toFixed(1)} Δframe=${d.frame?.toFixed(1)} Δtop=${d.topbar?.toFixed(1)} Δside=${d.sidebar?.toFixed(1)} CLS=${row.layoutShiftValue}`,
    );
  }
}

void main();
