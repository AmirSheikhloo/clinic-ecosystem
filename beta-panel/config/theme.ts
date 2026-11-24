/** Global theme identifiers — preference only; never store patient data here. */

export type ThemeId = "ocean" | "midnight" | "emerald" | "graphite";
export type Appearance = "light" | "dark";

export const THEME_STORAGE_KEY = "ce_beta_theme_pref";
export const APPEARANCE_STORAGE_KEY = "ce_beta_appearance_pref";

export const THEME_LABELS: Record<ThemeId, string> = {
  ocean: "اقیانوس",
  midnight: "نیمه‌شب",
  emerald: "زمردی",
  graphite: "گرافیت",
};

export const DEFAULT_THEME: ThemeId = "ocean";
export const DEFAULT_APPEARANCE: Appearance = "light";

export function isThemeId(value: string): value is ThemeId {
  return value in THEME_LABELS;
}

export function isAppearance(value: string): value is Appearance {
  return value === "light" || value === "dark";
}
