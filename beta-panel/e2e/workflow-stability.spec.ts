/** Workspace-level stability: stable grids while data loads, calendar lanes, filter links, table columns. */
import { expect, test, type Page } from "@playwright/test";
import { tehranTodayYmd } from "../lib/tehran";
import { bff, credsFromEnv, deskBook, deskRegisterPatient, loginAs, RUN, tehranSlot } from "./ops-helpers";

test.use({ launchOptions: { ignoreDefaultArgs: ["--hide-scrollbars"] } });
test.describe.configure({ mode: "serial" });

type Box = { x: number; y: number; width: number; height: number };

/** Document-relative rectangle, so scroll position never counts as movement. */
async function box(page: Page, testId: string): Promise<Box> {
  const found = await page.getByTestId(testId).first().evaluate((node) => {
    const rect = node.getBoundingClientRect();
    return { x: rect.x + window.scrollX, y: rect.y + window.scrollY, width: rect.width, height: rect.height };
  });
  return found;
}

function same(label: string, a: Box, b: Box, tolerance = 1) {
  for (const key of ["x", "y", "width", "height"] as const) {
    expect(Math.abs(a[key] - b[key]), `${label}: ${key} ${a[key]} vs ${b[key]}`).toBeLessThanOrEqual(tolerance);
  }
}

/** A booking in a slot used by an earlier run needs the overlap acknowledgement; both outcomes are fine here. */
async function acknowledgeIfAsked(page: Page) {
  const dialog = page.getByTestId("overlap-dialog");
  const status = page.getByTestId("desk-status");
  await expect(dialog.or(status)).toBeVisible({ timeout: 45_000 });
  if (await dialog.isVisible()) {
    await page.getByTestId("overlap-confirm").click();
    await expect(status).toBeVisible({ timeout: 45_000 });
  }
}

test("dashboard cards keep their geometry while the summary loads", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 45_000 });
  const loaded = { actions: await box(page, "dashboard-quick-actions"), metrics: await box(page, "dashboard-metrics") };

  await page.route("**/api/v1/dashboard/summary**", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await route.continue();
  });
  await page.reload();
  await expect(page.getByTestId("dashboard-metrics")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-count")).toHaveCount(0);
  const loading = { actions: await box(page, "dashboard-quick-actions"), metrics: await box(page, "dashboard-metrics") };
  same("quick actions while loading", loaded.actions, loading.actions);
  same("metric grid while loading", loaded.metrics, loading.metrics);
  await expect(page.getByTestId("dashboard-count")).toBeVisible({ timeout: 30_000 });
  same("metric grid after load", loaded.metrics, await box(page, "dashboard-metrics"));
});

test("dashboard status chips link to a filtered calendar day", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  const today = tehranTodayYmd();
  await page.goto(`/appointments?date=${today}&view=week&status=CONFIRMED`);
  await expect(page.getByTestId("appointments-page")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByTestId("filter-status")).toHaveValue("CONFIRMED");
  await expect(page.getByTestId("view-week")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("filters-clear")).toBeEnabled();
});

test("calendar: overlapping visits sit in separate lanes and the toolbar does not move between views", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  const slot = tehranSlot(0, 18);
  await page.goto("/desk");
  await expect(page.getByTestId("desk-page")).toBeVisible({ timeout: 45_000 });
  await deskRegisterPatient(page, "Lane", `A${RUN}`);
  await expect(page.getByTestId("summary-patient")).toContainText(`Lane A${RUN}`);
  await deskBook(page, slot);
  await acknowledgeIfAsked(page);
  await expect(page.getByTestId("summary-service")).not.toHaveText("—");
  await deskRegisterPatient(page, "Lane", `B${RUN}`);
  await deskBook(page, slot);
  await expect(page.getByTestId("overlap-dialog")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByTestId("overlap-dialog")).not.toContainText("01a");
  await page.getByTestId("overlap-confirm").click();
  await expect(page.getByTestId("desk-status")).toContainText("تأیید تداخل", { timeout: 45_000 });

  await page.goto("/appointments?view=day");
  await expect(page.getByTestId("appointments-page")).toBeVisible({ timeout: 30_000 });
  const events = page.getByTestId("timeline-event").filter({ hasText: `${RUN}` });
  await expect(events).toHaveCount(2, { timeout: 30_000 });
  const [first, second] = await Promise.all([events.nth(0).boundingBox(), events.nth(1).boundingBox()]);
  const apart = first!.x + first!.width <= second!.x + 1 || second!.x + second!.width <= first!.x + 1;
  expect(apart, "overlapping appointments share the row side by side").toBe(true);
  await events.nth(0).click();
  await expect(page.getByTestId("appointment-dialog")).toBeVisible({ timeout: 20_000 });
  await page.keyboard.press("Escape");

  const parts = ["calendar-view", "filters-clear", "sort-select", "filter-status"];
  const day: Record<string, Box> = {};
  for (const id of parts) day[id] = await box(page, id);
  for (const view of ["week", "month"] as const) {
    await page.getByTestId(`view-${view}`).click();
    await expect(page.getByTestId(view === "week" ? "week-view" : "month-view")).toBeVisible();
    for (const id of parts) same(`${id} in ${view}`, day[id], await box(page, id));
  }
  const bff200 = await bff(page, "GET", "/api/auth/me");
  expect(bff200.status).toBe(200);
});

test("patient table columns keep their widths across result sets", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/patients");
  await expect(page.getByTestId("patients-result-row").first()).toBeVisible({ timeout: 45_000 });
  const widths = () => page.locator("table.ds-table th").evaluateAll((cells) => cells.map((cell) => Math.round(cell.getBoundingClientRect().width)));
  const all = await widths();
  await page.getByTestId("patients-search-query").fill(`A${RUN}`);
  await page.getByTestId("patients-search-submit").click();
  await expect(page.getByTestId("patients-result-row")).toHaveCount(1, { timeout: 30_000 });
  const filtered = await widths();
  expect(filtered).toEqual(all);
});

test("stale directory rows are marked busy, never shown as the new result", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/patients");
  await expect(page.getByTestId("patients-result-row").first()).toBeVisible({ timeout: 45_000 });
  await page.route("**/api/v1/patients/directory**", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.continue();
  });
  await page.getByTestId("patients-status-filter").selectOption("inactive");
  await expect(page.locator(".ds-table-wrap[data-busy='true']")).toBeVisible();
  await expect(page.locator(".ds-table-wrap[data-busy='true']")).toHaveCount(0, { timeout: 15_000 });
});
