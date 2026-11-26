/**
 * Browser-local, non-sensitive display preferences. One module owns the keys, allowed values,
 * defaults and the pre-hydration boot script, so the server markup, the boot script and the
 * client store can never disagree. Never store patient, tenant or authentication data here.
 */
import {
  APPEARANCE_STORAGE_KEY,
  DEFAULT_THEME,
  THEME_LABELS,
  THEME_STORAGE_KEY,
  type Appearance,
  type ThemeId,
} from "./theme";

export type AppearancePreference = Appearance | "system";
export type Density = "comfortable" | "compact";
export type SidebarPreference = "expanded" | "collapsed";
export type MotionPreference = "system" | "reduced";

export type Preferences = {
  theme: ThemeId;
  appearance: AppearancePreference;
  density: Density;
  sidebar: SidebarPreference;
  motion: MotionPreference;
};

export const DENSITY_STORAGE_KEY = "ce_beta_density_pref";
export const SIDEBAR_STORAGE_KEY = "ce_beta_sidebar_pref";
export const MOTION_STORAGE_KEY = "ce_beta_motion_pref";

export const STORAGE_KEYS: Record<keyof Preferences, string> = {
  theme: THEME_STORAGE_KEY,
  appearance: APPEARANCE_STORAGE_KEY,
  density: DENSITY_STORAGE_KEY,
  sidebar: SIDEBAR_STORAGE_KEY,
  motion: MOTION_STORAGE_KEY,
};

export const DEFAULT_PREFERENCES: Preferences = {
  theme: DEFAULT_THEME,
  appearance: "light",
  density: "comfortable",
  sidebar: "expanded",
  motion: "system",
};

export const ALLOWED_VALUES: { [K in keyof Preferences]: readonly Preferences[K][] } = {
  theme: Object.keys(THEME_LABELS) as ThemeId[],
  appearance: ["light", "dark", "system"],
  density: ["comfortable", "compact"],
  sidebar: ["expanded", "collapsed"],
  motion: ["system", "reduced"],
};

export const APPEARANCE_LABELS: Record<AppearancePreference, string> = {
  light: "روشن",
  dark: "تیره",
  system: "مطابق سیستم",
};
export const DENSITY_LABELS: Record<Density, string> = { comfortable: "راحت", compact: "فشرده" };
export const SIDEBAR_LABELS: Record<SidebarPreference, string> = { expanded: "باز", collapsed: "جمع‌شده" };
export const MOTION_LABELS: Record<MotionPreference, string> = {
  system: "مطابق سیستم",
  reduced: "کاهش حرکت",
};

export function parsePreference<K extends keyof Preferences>(key: K, raw: string | null): Preferences[K] {
  const allowed = ALLOWED_VALUES[key] as readonly string[];
  return (raw !== null && allowed.includes(raw) ? raw : DEFAULT_PREFERENCES[key]) as Preferences[K];
}

export function resolveAppearance(preference: AppearancePreference, systemPrefersDark: boolean): Appearance {
  if (preference === "system") return systemPrefersDark ? "dark" : "light";
  return preference;
}

/**
 * Runs in <head> before first paint so the saved palette, density and sidebar width are applied
 * without a flash or a layout jump. Keep it dependency-free; values are validated against the
 * same allow-lists as the client store.
 */
export const PREFERENCES_BOOT_SCRIPT = `(function(){try{var d=document.documentElement,s=localStorage,a=${JSON.stringify(
  ALLOWED_VALUES,
)},k=${JSON.stringify(STORAGE_KEYS)},df=${JSON.stringify(DEFAULT_PREFERENCES)};function g(n){var v=s.getItem(k[n]);return a[n].indexOf(v)>=0?v:df[n]}var ap=g("appearance");if(ap==="system"){ap=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}d.dataset.theme=g("theme");d.dataset.appearance=ap;d.dataset.density=g("density");d.dataset.sidebar=g("sidebar");d.dataset.motion=g("motion")}catch(e){}})();`;
