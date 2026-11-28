/**
 * Shell geometry regression suite (real BFF + API + PG15, synthetic data).
 *
 * Contract: the sidebar, top bar, Tehran clock slot, account controls and the page frame keep the
 * same position and size across navigation, loading, long names, dialogs and scrollbar changes at a
 * given viewport and sidebar mode (tolerance: 1 CSS px). Rectangles are sampled on every animation
 * frame while the interaction runs, so intermediate movement is measured and not only the settled
 * state. Layout-shift entries are recorded too; limitation: Chrome flags shifts that follow a
 * user input within 500 ms as `hadRecentInput` and excludes them from the CLS score, so CLS is
 * only a supporting signal here (we count every entry) and frame sampling is authoritative.
 */
import { expect, test, type Page } from "@playwright/test";
import {
  maxFrameDeviation,
  rectDeltas,
  shellRects,
  startSampling,
  stopSampling,
  type ShellPart,
} from "./layout-geometry";
import { navLink } from "./helpers";
import { bff, credsFromEnv, loginAs, RUN } from "./ops-helpers";

// Headless Chromium hides scrollbars by default, which would hide the main historical cause.
test.use({ launchOptions: { ignoreDefaultArgs: ["--hide-scrollbars"] } });
test.describe.configure({ mode: "serial" });

const TOLERANCE = 1;
const PARTS: ShellPart[] = ["sidebar", "topbar", "clock", "account", "frame"];
const PAGES: [label: string, path: string][] = [
  ["داشبورد", "/dashboard"],
  ["میز پذیرش", "/desk"],
  ["مدیریت نوبت‌ها", "/appointments"],
  ["بیماران", "/patients"],
  ["خدمات و منابع", "/catalog"],
  ["کارکنان", "/staff"],
  ["کاربران و دسترسی", "/access"],
  ["ظاهر و ترجیحات", "/preferences"],
];
const VIEWPORTS = [
  { width: 1280, height: 800 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
];

function expectWithin(label: string, deltas: Partial<Record<ShellPart, number>>) {
  for (const part of PARTS) {
    expect(deltas[part] ?? 0, `${label}: ${part} moved`).toBeLessThanOrEqual(TOLERANCE);
  }
}

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(450);
}

async function walkWorkspaces(page: Page, label: string) {
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 45_000 });
  await settle(page);
  const reference = await shellRects(page);
  const seenScroll = new Set<boolean>();
  for (const [name, path] of PAGES) {
    await startSampling(page);
    await navLink(page, name).click();
    await page.waitForURL(`**${path}`);
    await settle(page);
    const samples = await stopSampling(page);
    const settled = await shellRects(page);
    expectWithin(`${label} ${path} settled`, rectDeltas(reference, settled));
    expectWithin(`${label} ${path} per-frame`, maxFrameDeviation(samples));
    expect(samples.shellShifts, `${label} ${path}: layout shifts inside shell`).toBe(0);
    seenScroll.add(await page.evaluate(() => document.documentElement.scrollHeight > window.innerHeight));
  }
  return seenScroll;
}

for (const viewport of VIEWPORTS) {
  test(`shell geometry is stable across workspaces at ${viewport.width}px (expanded sidebar)`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await loginAs(page, credsFromEnv("OWNER"), "owner");
    const seenScroll = await walkWorkspaces(page, `${viewport.width} expanded`);
    if (viewport.width === 1280) {
      // Short pages and pages with a vertical scrollbar are both covered.
      expect(seenScroll.has(true) && seenScroll.has(false)).toBe(true);
    }
  });

  test(`shell geometry is stable across workspaces at ${viewport.width}px (collapsed sidebar)`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await loginAs(page, credsFromEnv("OWNER"), "owner");
    await page.getByTestId("sidebar-toggle").click();
    await expect(page.getByTestId("sidebar-toggle")).toHaveAttribute("aria-expanded", "false");
    await page.waitForTimeout(450);
    const rail = await page.getByTestId("app-sidebar").boundingBox();
    expect(rail!.width).toBeLessThan(80);
    await walkWorkspaces(page, `${viewport.width} collapsed`);
  });
}

test("sidebar width is identical on every page in both modes", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  const widths: Record<string, Set<number>> = { expanded: new Set(), collapsed: new Set() };
  for (const mode of ["expanded", "collapsed"] as const) {
    if (mode === "collapsed") {
      await page.getByTestId("sidebar-toggle").click();
      await page.waitForTimeout(450);
    }
    for (const [name] of PAGES) {
      await navLink(page, name).click();
      await settle(page);
      widths[mode].add(Math.round((await page.getByTestId("app-sidebar").boundingBox())!.width));
    }
    expect(widths[mode].size, `${mode} widths: ${[...widths[mode]]}`).toBe(1);
  }
});

test("long account names and breadcrumbs do not resize the clock or account areas", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  const created = await bff(page, "POST", "/api/patients", {
    body: { first_name: "نام‌بسیار‌طولانی‌برای‌آزمون‌چیدمان", last_name: `Long${RUN}` },
  });
  expect(created.status).toBe(201);
  const profileId = String((created.body as { patient_profile_id?: string }).patient_profile_id);

  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 45_000 });
  await settle(page);
  const reference = await shellRects(page);

  await page.route("**/api/auth/me", async (route) => {
    const response = await route.fetch();
    const body = (await response.json()) as Record<string, unknown>;
    body.first_name = "نام‌بسیار‌بسیار‌طولانی‌برای‌بررسی‌برش‌متن‌در‌نوار‌بالا";
    body.last_name = "Extraordinarily-Long-Family-Name-For-Truncation-Check";
    await route.fulfill({ response, json: body });
  });
  await page.reload();
  await expect(page.getByTestId("current-user")).toContainText("Extraordinarily");
  await settle(page);
  expectWithin("long account name", rectDeltas(reference, await shellRects(page)));
  const chip = await page.getByTestId("current-user").evaluate((node) => {
    // Prefer the display-name line; the outer flex wrapper may not overflow once children truncate.
    const label =
      (node.querySelector("span.block.truncate") as HTMLElement | null) ??
      (node.querySelector(".truncate") as HTMLElement | null);
    return {
      truncated: Boolean(label && label.scrollWidth > label.clientWidth),
      overflowsChip: node.scrollWidth > node.clientWidth + 1,
    };
  });
  expect(chip.truncated).toBe(true);
  expect(chip.overflowsChip).toBe(false);

  for (const path of ["/patients", `/patients/${profileId}`, "/catalog/manage"]) {
    await page.goto(path);
    await settle(page);
    const settled = await shellRects(page);
    expectWithin(`breadcrumb ${path}`, rectDeltas(reference, settled));
    const crumbs = await page.getByTestId("breadcrumbs").evaluate((node) => {
      const list = node.querySelector("ol") as HTMLElement;
      return { contained: list.scrollWidth <= list.clientWidth + 1 || getComputedStyle(list).overflow === "hidden" };
    });
    expect(crumbs.contained).toBe(true);
  }
});

test("narrow desktop width truncates breadcrumbs inside their column", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 45_000 });
  await settle(page);
  const reference = await shellRects(page);
  for (const path of ["/appointments", "/catalog/manage", "/access"]) {
    await page.goto(path);
    await settle(page);
    expectWithin(`1024 ${path}`, rectDeltas(reference, await shellRects(page)));
    const rects = await shellRects(page);
    const crumbBox = (await page.getByTestId("breadcrumbs").boundingBox())!;
    const apart = (a: { x: number; width: number }, b: { x: number; width: number }) =>
      a.x + a.width <= b.x + TOLERANCE || b.x + b.width <= a.x + TOLERANCE;
    expect(apart(rects.clock!, rects.account!), "clock and account overlap").toBe(true);
    expect(apart(crumbBox, rects.clock!), "breadcrumbs overlap clock").toBe(true);
    expect(apart(crumbBox, rects.account!), "breadcrumbs overlap account").toBe(true);
    expect(crumbBox.x).toBeGreaterThanOrEqual(rects.topbar!.x - TOLERANCE);
    expect(crumbBox.x + crumbBox.width).toBeLessThanOrEqual(rects.topbar!.x + rects.topbar!.width + TOLERANCE);
  }
});

test("delayed session and data responses keep the shell fixed (skeletons hold the geometry)", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 45_000 });
  await settle(page);
  const reference = await shellRects(page);

  await page.route("**/api/auth/me", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });
  await page.reload({ waitUntil: "commit" });
  await expect(page.getByTestId("app-sidebar")).toBeVisible();
  await expect(page.getByTestId("topbar-account")).toBeVisible();
  await expect(page.getByTestId("current-user")).toHaveCount(0);
  const loading = await shellRects(page);
  expectWithin("session loading (skeleton) vs loaded", rectDeltas(reference, loading));
  await expect(page.getByTestId("current-user")).toBeVisible({ timeout: 30_000 });
  await settle(page);
  expectWithin("after delayed session", rectDeltas(reference, await shellRects(page)));
  await page.unroute("**/api/auth/me");

  await page.route("**/api/**", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    await route.continue();
  });
  await startSampling(page);
  await navLink(page, "بیماران").click();
  await page.waitForURL("**/patients");
  await expect(page.getByTestId("patients-page")).toBeVisible({ timeout: 30_000 });
  await settle(page);
  const nav = await stopSampling(page);
  expectWithin("delayed navigation per-frame", maxFrameDeviation(nav));
  expect(nav.shellShifts).toBe(0);
  await page.unroute("**/api/**");
});

test("dialogs and drawers open and close without moving the shell", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  // Top-bar theme menu removed (UX-04); exercise patient register dialog only.
  await page.goto("/patients");
  await settle(page);
  const reference = await shellRects(page);
  await startSampling(page);
  await page.getByTestId("patients-new").click();
  await page.waitForTimeout(500);
  await expect(page.getByTestId("patients-register-dialog")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-scroll-locked", "true");
  const topmost = await page.getByTestId("patients-register-dialog").evaluate((panel) => {
    const box = panel.getBoundingClientRect();
    const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
    return Boolean(hit && panel.contains(hit));
  });
  expect(topmost).toBe(true);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const samples = await stopSampling(page);
  expectWithin("/patients overlay per-frame", maxFrameDeviation(samples));
  expectWithin("/patients overlay settled", rectDeltas(reference, await shellRects(page)));
  await expect(page.locator("html")).not.toHaveAttribute("data-scroll-locked", "true");
});

test("navigation does not remount the shell and keeps the same DOM nodes", async ({ page }) => {
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 45_000 });
  await page.evaluate(() => {
    const w = window as unknown as { __shell: Element[] };
    w.__shell = ["app-sidebar", "app-topbar", "tehran-clock", "topbar-account"].map(
      (id) => document.querySelector(`[data-testid="${id}"]`)!,
    );
  });
  for (const [name, path] of PAGES.slice(1)) {
    await navLink(page, name).click();
    await page.waitForURL(`**${path}`);
  }
  const same = await page.evaluate(() => {
    const w = window as unknown as { __shell: Element[] };
    return ["app-sidebar", "app-topbar", "tehran-clock", "topbar-account"].every(
      (id, index) => document.querySelector(`[data-testid="${id}"]`) === w.__shell[index] && w.__shell[index].isConnected,
    );
  });
  expect(same).toBe(true);
});
