/**
 * Module-level store for display preferences, consumed with `useSyncExternalStore`.
 * The server snapshot is always the defaults; the client snapshot is read lazily from
 * localStorage, so there is no hydration mismatch and no effect-driven state copy.
 */
import {
  DEFAULT_PREFERENCES,
  STORAGE_KEYS,
  parsePreference,
  resolveAppearance,
  type Preferences,
} from "@/config/preferences";

let snapshot: Preferences | null = null;
const listeners = new Set<() => void>();

function readStored(): Preferences {
  const next = { ...DEFAULT_PREFERENCES };
  try {
    (Object.keys(STORAGE_KEYS) as (keyof Preferences)[]).forEach((key) => {
      (next as Record<string, string>)[key] = parsePreference(key, localStorage.getItem(STORAGE_KEYS[key]));
    });
  } catch {
    /* storage unavailable: defaults apply */
  }
  return next;
}

export function getPreferencesSnapshot(): Preferences {
  snapshot ??= readStored();
  return snapshot;
}

export function getServerPreferences(): Preferences {
  return DEFAULT_PREFERENCES;
}

export function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Mirrors preferences onto <html> so CSS tokens and the shell geometry react to them. */
export function applyPreferencesToDom(prefs: Preferences): void {
  const root = document.documentElement;
  root.dataset.theme = prefs.theme;
  root.dataset.appearance = resolveAppearance(prefs.appearance, systemPrefersDark());
  root.dataset.density = prefs.density;
  root.dataset.sidebar = prefs.sidebar;
  root.dataset.motion = prefs.motion;
}

/** Writes the effective values so storage always mirrors what the page is showing. */
export function persistPreferences(prefs: Preferences): void {
  try {
    (Object.keys(STORAGE_KEYS) as (keyof Preferences)[]).forEach((key) => {
      localStorage.setItem(STORAGE_KEYS[key], prefs[key]);
    });
  } catch {
    /* non-sensitive preference only */
  }
}

function emit() {
  listeners.forEach((listener) => listener());
}

/** Brief class on <html> enabling the centralized theme color transition (see motion.css). */
function markThemeSwitch() {
  const root = document.documentElement;
  root.classList.add("ds-theme-switching");
  window.setTimeout(() => root.classList.remove("ds-theme-switching"), 360);
}

export function setPreference<K extends keyof Preferences>(key: K, value: Preferences[K]): void {
  const current = getPreferencesSnapshot();
  if (current[key] === value) return;
  if (key === "theme" || key === "appearance") markThemeSwitch();
  snapshot = { ...current, [key]: value };
  persistPreferences(snapshot);
  applyPreferencesToDom(snapshot);
  emit();
}

export function resetPreferences(): void {
  markThemeSwitch();
  snapshot = { ...DEFAULT_PREFERENCES };
  try {
    (Object.keys(STORAGE_KEYS) as (keyof Preferences)[]).forEach((key) => localStorage.removeItem(STORAGE_KEYS[key]));
  } catch {
    /* ignore */
  }
  applyPreferencesToDom(snapshot);
  emit();
}

export function subscribePreferences(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || Object.values(STORAGE_KEYS).includes(event.key)) {
      snapshot = readStored();
      applyPreferencesToDom(snapshot);
      listener();
    }
  };
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onMedia = () => {
    applyPreferencesToDom(getPreferencesSnapshot());
    listener();
  };
  window.addEventListener("storage", onStorage);
  media.addEventListener("change", onMedia);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
    media.removeEventListener("change", onMedia);
  };
}

export function getSystemDarkSnapshot(): boolean {
  return systemPrefersDark();
}
