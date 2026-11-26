"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";
import type { Appearance, ThemeId } from "@/config/theme";
import {
  resolveAppearance,
  type AppearancePreference,
  type Preferences,
} from "@/config/preferences";
import {
  applyPreferencesToDom,
  getPreferencesSnapshot,
  getServerPreferences,
  getSystemDarkSnapshot,
  persistPreferences,
  resetPreferences,
  setPreference,
  subscribePreferences,
} from "@/lib/preferences-store";

type PreferencesContextValue = {
  preferences: Preferences;
  /** Appearance after resolving "system". */
  appearance: Appearance;
  theme: ThemeId;
  setPreference: typeof setPreference;
  resetPreferences: () => void;
  setTheme: (theme: ThemeId) => void;
  setAppearance: (appearance: AppearancePreference) => void;
  toggleAppearance: () => void;
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

const serverDark = () => false;

export function ThemeProvider({ children }: { children: ReactNode }) {
  const preferences = useSyncExternalStore(subscribePreferences, getPreferencesSnapshot, getServerPreferences);
  const systemDark = useSyncExternalStore(subscribePreferences, getSystemDarkSnapshot, serverDark);
  const appearance = resolveAppearance(preferences.appearance, systemDark);

  useEffect(() => {
    applyPreferencesToDom(preferences);
    persistPreferences(preferences);
  }, [preferences]);

  const setTheme = useCallback((theme: ThemeId) => setPreference("theme", theme), []);
  const setAppearance = useCallback((value: AppearancePreference) => setPreference("appearance", value), []);
  const toggleAppearance = useCallback(
    () => setPreference("appearance", resolveAppearance(getPreferencesSnapshot().appearance, getSystemDarkSnapshot()) === "light" ? "dark" : "light"),
    [],
  );

  const value = useMemo<PreferencesContextValue>(
    () => ({
      preferences,
      appearance,
      theme: preferences.theme,
      setPreference,
      resetPreferences,
      setTheme,
      setAppearance,
      toggleAppearance,
    }),
    [preferences, appearance, setTheme, setAppearance, toggleAppearance],
  );

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreferences must be used within ThemeProvider");
  return ctx;
}

/** Palette and appearance subset of the preferences, kept for the quick theme menu. */
export function useTheme() {
  return usePreferences();
}
