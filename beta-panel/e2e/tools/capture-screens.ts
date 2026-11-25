/**
 * Screenshot capture for visual review (not part of the Playwright suite).
 * Usage: BETA01B_E2E_ENV_FILE=... SHOT_DIR=... npx tsx e2e/tools/capture-screens.ts
 * Seeds a few synthetic patients and appointments through the BFF, then captures key screens.
 */
import { chromium, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { shiftTehranYmd as addDays, tehranTodayYmd } from "../../lib/tehran";

function loadEnv(file: string) {
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const idx = line.indexOf("=");
    if (idx > 0 && !process.env[line.slice(0, idx)]) process.env[line.slice(0, idx)] = line.slice(idx + 1);
  }
}

type Json = Record<string, unknown> | null;

async function bff(page: Page, method: string, url: string, body?: unknown, headers: Record<string, string> = {}) {
  return page.evaluate(
    async ({ method, url, body, headers }) => {
      const token = decodeURIComponent(
        document.cookie.split("; ").find((c) => c.startsWith("ce_beta_csrf="))?.split("=")[1] ?? "",
      );
      const res = await fetch(url, {
        method,
        credentials: "same-origin",
        headers: { "content-type": "application/json", "x-csrf-token": token, ...headers },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return { status: res.status, body: (await res.json().catch(() => null)) as Json };
    },
    { method, url, body, headers },
  );
}

async function main() {
  const envFile = process.env.BETA01B_E2E_ENV_FILE;
  if (envFile) loadEnv(envFile);
  const base = process.env.BETA01B_PANEL_BASE_URL!;
  const out = process.env.SHOT_DIR || "/tmp/shots";
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "fa-IR", baseURL: base });
  const page = await context.newPage();
  await page.goto("/login");
  await page.evaluate(() => fetch("/api/auth/csrf", { credentials: "same-origin" }));
  await page.waitForTimeout(300);
  await page.getByTestId("login-identifier").fill(process.env.BETA02_OWNER_LOGIN!);
  await page.getByTestId("login-password").fill(process.env.BETA02_OWNER_PASSWORD!);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/(desk|dashboard)/, { timeout: 45_000 });

  const run = Date.now().toString().slice(-5);
  const names = [
    ["مریم", "احمدی"],
    ["علی", "رضایی"],
    ["سارا", "کریمی"],
    ["نیما", "حسینی"],
  ];
  const patients: string[] = [];
  for (const [first, last] of names) {
    const r = await bff(page, "POST", "/api/patients", { first_name: first, last_name: `${last}${run}`, birth_date: "1990-03-21" });
    const id = (r.body as { patient_profile_id?: string } | null)?.patient_profile_id;
    if (id) patients.push(id);
  }
  const services = (await bff(page, "GET", "/api/catalog/services")).body as { items?: Array<{ id?: string; service_id?: string }> } | Array<{ id?: string }> | null;
  const resources = (await bff(page, "GET", "/api/catalog/resources")).body as { items?: Array<{ id?: string }> } | Array<{ id?: string }> | null;
  const svcList = (Array.isArray(services) ? services : services?.items ?? []) as Array<{ id?: string; service_id?: string; service_name?: string }>;
  const resList = (Array.isArray(resources) ? resources : resources?.items ?? []) as Array<{ id?: string; resource_name?: string }>;
  const svc = svcList.find((s) => s.service_name === process.env.BETA01B_SERVICE_NAME) ?? svcList[0];
  const res = resList.find((r) => r.resource_name === process.env.BETA01B_RESOURCE_NAME) ?? resList[0];
  const today = tehranTodayYmd();
  if (svc && res) {
    const slots = [[0, "09:00"], [0, "10:30"], [0, "13:00"], [1, "09:30"], [2, "11:00"], [-1, "15:00"]] as const;
    for (const [i, [offset, time]] of slots.entries()) {
      const { tehranLocalToUtcIso } = await import("../../lib/tehran");
      const startIso = tehranLocalToUtcIso(`${addDays(today, offset)}T${time}`);
      const endIso = new Date(new Date(startIso).getTime() + 30 * 60_000).toISOString();
      const booked = await bff(
        page,
        "POST",
        "/api/appointments",
        {
          beneficiary_patient_id: patients[i % patients.length],
          service_id: svc.id ?? svc.service_id,
          resource_ids: [res.id],
          start_at_utc: startIso,
          end_at_utc: endIso,
          booking_channel: "MANUAL_STAFF",
          capacity_pool: "MANUAL",
          acknowledge_overlap: true,
          acknowledged_conflict_ids: [],
        },
        { "Idempotency-Key": `shot-${run}-${i}-xxxxxxxx` },
      );
      if (booked.status >= 300) console.log("booking", i, booked.status, JSON.stringify(booked.body).slice(0, 200));
    }
  }

  const shots: Array<[string, string, (p: Page) => Promise<void>?]> = [
    ["dashboard", "/dashboard"],
    ["desk", "/desk"],
    ["patients", "/patients"],
    ["appointments-day", "/appointments"],
    ["catalog", "/catalog"],
    ["catalog-manage", "/catalog/manage"],
    ["staff", "/staff"],
    ["access", "/access"],
  ];
  for (const [name, url] of shots) {
    await page.goto(url);
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(out, `${name}.png`) });
  }
  await page.goto("/appointments");
  await page.waitForTimeout(800);
  for (const view of ["week", "month"]) {
    await page.getByTestId(`view-${view}`).click();
    await page.waitForTimeout(900);
    await page.screenshot({ path: path.join(out, `appointments-${view}.png`) });
  }
  await page.goto("/patients");
  await page.waitForTimeout(800);
  await page.getByTestId("patients-open-profile").first().click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(out, "patient-profile.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(out, "mobile-dashboard.png") });
  await browser.close();
  console.log("captured", fs.readdirSync(out).length, "screenshots in", out);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
