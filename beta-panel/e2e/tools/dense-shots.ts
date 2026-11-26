/**
 * Dense-data visual check (not part of the Playwright suite): long names, six simultaneous visits,
 * out-of-hours visits, then screenshots of the affected screens.
 * Usage: BETA01B_E2E_ENV_FILE=... SHOT_DIR=... npx tsx e2e/tools/dense-shots.ts
 */
import { chromium, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { tehranLocalToUtcIso, tehranTodayYmd } from "../../lib/tehran";

function loadEnv(file: string) {
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const idx = line.indexOf("=");
    if (idx > 0 && !process.env[line.slice(0, idx)]) process.env[line.slice(0, idx)] = line.slice(idx + 1);
  }
}

async function bff(page: Page, method: string, url: string, body?: unknown, headers: Record<string, string> = {}) {
  return page.evaluate(
    async ({ method, url, body, headers }) => {
      const token = decodeURIComponent(document.cookie.split("; ").find((c) => c.startsWith("ce_beta_csrf="))?.split("=")[1] ?? "");
      const res = await fetch(url, {
        method,
        credentials: "same-origin",
        headers: { "content-type": "application/json", "x-csrf-token": token, ...headers },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return { status: res.status, body: (await res.json().catch(() => null)) as Record<string, unknown> | null };
    },
    { method, url, body, headers },
  );
}

async function main() {
  if (process.env.BETA01B_E2E_ENV_FILE) loadEnv(process.env.BETA01B_E2E_ENV_FILE);
  const out = process.env.SHOT_DIR || "/tmp/dense";
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "fa-IR", baseURL: process.env.BETA01B_PANEL_BASE_URL });
  const page = await context.newPage();
  await page.goto("/login");
  await page.evaluate(() => fetch("/api/auth/csrf", { credentials: "same-origin" }));
  await page.waitForTimeout(300);
  await page.getByTestId("login-identifier").fill(process.env.BETA02_OWNER_LOGIN!);
  await page.getByTestId("login-password").fill(process.env.BETA02_OWNER_PASSWORD!);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/(desk|dashboard)/, { timeout: 45_000 });

  const run = Date.now().toString().slice(-5);
  const services = ((await bff(page, "GET", "/api/catalog/services")).body as { items: Array<{ id: string; service_name: string }> }).items;
  const resources = ((await bff(page, "GET", "/api/catalog/resources")).body as { items: Array<{ id: string; resource_name: string }> }).items;
  const service = services.find((item) => item.service_name === process.env.BETA01B_SERVICE_NAME) ?? services[0];
  const resource = resources.find((item) => item.resource_name === process.env.BETA01B_RESOURCE_NAME) ?? resources[0];
  const today = tehranTodayYmd();
  const slots = ["06:30", "09:00", "09:00", "09:00", "09:15", "09:20", "09:30", "12:00", "21:15"];
  for (const [index, time] of slots.entries()) {
    const long = index === 1;
    const created = await bff(page, "POST", "/api/patients", {
      first_name: long ? "نام‌بسیار‌طولانی‌بیمار‌برای‌آزمون‌برش‌متن" : `بیمار${index}`,
      last_name: long ? `Extraordinarily-Long-Family-Name-${run}` : `آزمون${run}`,
    });
    const patientId = (created.body as { patient_profile_id?: string } | null)?.patient_profile_id;
    const start = tehranLocalToUtcIso(`${today}T${time}`);
    const end = new Date(new Date(start).getTime() + (index === 7 ? 90 : 30) * 60_000).toISOString();
    const payload = {
      beneficiary_patient_id: patientId,
      service_id: service.id,
      resource_ids: [resource.id],
      start_at_utc: start,
      end_at_utc: end,
      booking_channel: "MANUAL_STAFF",
      capacity_pool: "MANUAL",
      acknowledge_overlap: false,
      acknowledged_conflict_ids: [] as string[],
    };
    let booked = await bff(page, "POST", "/api/appointments", payload, { "Idempotency-Key": `dense-${run}-${index}-a` });
    if (booked.status === 409) {
      const detail = (booked.body?.detail ?? booked.body) as { conflicts?: Array<{ appointment_id?: string }> } | null;
      payload.acknowledge_overlap = true;
      payload.acknowledged_conflict_ids = (detail?.conflicts ?? []).map((c) => c.appointment_id!).filter(Boolean);
      booked = await bff(page, "POST", "/api/appointments", payload, { "Idempotency-Key": `dense-${run}-${index}-b` });
    }
    if (booked.status >= 300) console.log("booking", index, booked.status, JSON.stringify(booked.body).slice(0, 160));
  }
  for (const [name, url, full] of [
    ["day", "/appointments?view=day", true],
    ["week", "/appointments?view=week", false],
    ["month", "/appointments?view=month", false],
    ["patients", "/patients", false],
    ["dashboard", "/dashboard", true],
  ] as const) {
    await page.goto(url);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `dense-${name}.png`), fullPage: full });
  }
  await browser.close();
  console.log("done", out);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
