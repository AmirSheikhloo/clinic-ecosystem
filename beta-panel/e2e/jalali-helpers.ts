import type { Page } from "@playwright/test";
import { formatJalaliInput } from "../lib/calendar/jalali-input";

/** Types a Gregorian `YYYY-MM-DD` into a Jalali date control (the control shows and accepts Jalali text). */
export async function fillJalaliDate(page: Page, testId: string, ymd: string) {
  await page.getByTestId(testId).fill(formatJalaliInput(ymd));
}

/** Fills date and 24h time for a `JalaliDateTimeField` from a `YYYY-MM-DDTHH:mm` Tehran wall-clock value. */
export async function fillJalaliDateTime(page: Page, testId: string, local: string) {
  const [ymd, time] = local.split("T");
  await fillJalaliDate(page, testId, ymd);
  await page.getByTestId(`${testId}-time`).fill(time);
}

/** Opens the app theme menu so the theme controls become interactable. */
export async function openThemeMenu(page: Page) {
  await page.getByTestId("theme-menu-button").click();
}
