/**
 * Shell geometry measurement for layout-stability tests and evidence capture.
 * Rectangles are in CSS pixels. `sample*` records every animation frame so intermediate
 * movement (not only the settled state) is measured.
 */
import type { Page } from "@playwright/test";

/** Top-bar global search removed (UX-04); clock occupies the former search slot. */
export const SHELL_PARTS = {
  sidebar: '[data-testid="app-sidebar"]',
  topbar: '[data-testid="app-topbar"]',
  clock: '[data-testid="tehran-clock"]',
  account: '[data-testid="topbar-account"]',
  frame: '[data-testid="page-frame"]',
} as const;

/** The page frame grows with its content, so only its position and width are part of the contract. */
const CONTENT_HEIGHT_PARTS: ReadonlySet<string> = new Set(["frame"]);

export type ShellPart = keyof typeof SHELL_PARTS;
export type Rect = { x: number; y: number; width: number; height: number };
export type ShellRects = Partial<Record<ShellPart, Rect>>;

/** tsx/esbuild may inject a `__name` helper into evaluated functions; define it in the page. */
async function ensureHelpers(page: Page): Promise<void> {
  await page.evaluate("window.__name = window.__name || ((fn) => fn)");
}

/** Rectangles of each shared shell part right now. */
export async function shellRects(page: Page): Promise<ShellRects> {
  await ensureHelpers(page);
  return page.evaluate((parts) => {
    const out: Record<string, { x: number; y: number; width: number; height: number }> = {};
    for (const [name, selector] of Object.entries(parts)) {
      const node = document.querySelector(selector);
      if (!node) continue;
      const r = node.getBoundingClientRect();
      out[name] = { x: r.x, y: r.y, width: r.width, height: r.height };
    }
    return out;
  }, SHELL_PARTS);
}

/** Largest absolute difference of any edge/size between two measurements, per part. */
export function rectDeltas(a: ShellRects, b: ShellRects, parts: ShellPart[] = Object.keys(SHELL_PARTS) as ShellPart[]) {
  const result: Partial<Record<ShellPart, number>> = {};
  for (const part of parts) {
    const ra = a[part];
    const rb = b[part];
    if (!ra || !rb) {
      result[part] = Number.POSITIVE_INFINITY;
      continue;
    }
    result[part] = Math.max(
      Math.abs(ra.x - rb.x),
      Math.abs(ra.y - rb.y),
      Math.abs(ra.width - rb.width),
      CONTENT_HEIGHT_PARTS.has(part) ? 0 : Math.abs(ra.height - rb.height),
    );
  }
  return result;
}

export type FrameSamples = {
  frames: ShellRects[];
  shifts: number;
  shiftValue: number;
  /** Layout-shift entries whose moved node lives inside the sidebar or top bar. */
  shellShifts: number;
};

/** Begin per-frame sampling of shell rectangles plus layout-shift entries. */
export async function startSampling(page: Page): Promise<void> {
  await ensureHelpers(page);
  await page.evaluate((parts) => {
    const w = window as unknown as {
      __geo?: { frames: Record<string, unknown>[]; shifts: number; value: number; shell: number; stop: boolean };
    };
    const state = { frames: [] as Record<string, unknown>[], shifts: 0, value: 0, shell: 0, stop: false };
    w.__geo = state;
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const shift = entry as unknown as { value: number; sources?: { node: Node | null }[] };
          state.shifts += 1;
          state.value += shift.value;
          const inShell = (shift.sources ?? []).some((source) => {
            const element = source.node instanceof Element ? source.node : source.node?.parentElement;
            return Boolean(element?.closest('[data-testid="app-sidebar"], [data-testid="app-topbar"]'));
          });
          if (inShell) state.shell += 1;
        }
      }).observe({ type: "layout-shift", buffered: false });
    } catch {
      /* layout-shift unsupported: the frame sampler below is the primary measurement */
    }
    const tick = () => {
      if (state.stop) return;
      const frame: Record<string, unknown> = {};
      for (const [name, selector] of Object.entries(parts)) {
        const node = document.querySelector(selector);
        if (!node) continue;
        const r = node.getBoundingClientRect();
        frame[name] = { x: r.x, y: r.y, width: r.width, height: r.height };
      }
      state.frames.push(frame);
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, SHELL_PARTS);
}

export async function stopSampling(page: Page): Promise<FrameSamples> {
  return page.evaluate(() => {
    const w = window as unknown as {
      __geo?: { frames: Record<string, unknown>[]; shifts: number; value: number; shell: number; stop: boolean };
    };
    const state = w.__geo;
    if (!state) return { frames: [], shifts: 0, shiftValue: 0, shellShifts: 0 };
    state.stop = true;
    return { frames: state.frames as never, shifts: state.shifts, shiftValue: state.value, shellShifts: state.shell };
  });
}

/** Max per-part deviation of any sampled frame from the first sampled frame. */
export function maxFrameDeviation(samples: FrameSamples, parts: ShellPart[] = Object.keys(SHELL_PARTS) as ShellPart[]) {
  const [first, ...rest] = samples.frames;
  const result: Partial<Record<ShellPart, number>> = {};
  for (const part of parts) result[part] = 0;
  if (!first) return result;
  for (const frame of rest) {
    const deltas = rectDeltas(first, frame, parts);
    for (const part of parts) {
      result[part] = Math.max(result[part] ?? 0, deltas[part] ?? 0);
    }
  }
  return result;
}
