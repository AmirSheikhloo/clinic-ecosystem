"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  APPEARANCE_STORAGE_KEY,
  DEFAULT_APPEARANCE,
  DEFAULT_THEME,
  THEME_STORAGE_KEY,
  isAppearance,
  isThemeId,
  type Appearance,
  type ThemeId,
} from "@/config/theme";

type ThemeContextValue = {
  theme: ThemeId;
  appearance: Appearance;
  setTheme: (theme: ThemeId) => void;
  setAppearance: (appearance: Appearance) => void;
  toggleAppearance: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredTheme(): ThemeId {
  if (typeof window === "undefined") return DEFAULT_THEME;
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY) || "";
    return isThemeId(stored) ? stored : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

function readStoredAppearance(): Appearance {
  if (typeof window === "undefined") return DEFAULT_APPEARANCE;
  try {
    const stored = localStorage.getItem(APPEARANCE_STORAGE_KEY) || "";
    return isAppearance(stored) ? stored : DEFAULT_APPEARANCE;
  } catch {
    return DEFAULT_APPEARANCE;
  }
}

function applyDom(theme: ThemeId, appearance: Appearance) {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.dataset.appearance = appearance;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>(readStoredTheme);
  const [appearance, setAppearanceState] = useState<Appearance>(readStoredAppearance);

  useEffect(() => {
    applyDom(theme, appearance);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
      localStorage.setItem(APPEARANCE_STORAGE_KEY, appearance);
    } catch {
      /* non-sensitive preference only */
    }
  }, [theme, appearance]);

  const setTheme = useCallback((next: ThemeId) => {
    setThemeState(next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* non-sensitive preference only */
    }
  }, []);

  const setAppearance = useCallback((next: Appearance) => {
    setAppearanceState(next);
    try {
      localStorage.setItem(APPEARANCE_STORAGE_KEY, next);
    } catch {
      /* non-sensitive preference only */
    }
  }, []);

  const toggleAppearance = useCallback(() => {
    setAppearanceState((prev) => {
      const next = prev === "light" ? "dark" : "light";
      try {
        localStorage.setItem(APPEARANCE_STORAGE_KEY, next);
      } catch {
        /* non-sensitive preference only */
      }
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ theme, appearance, setTheme, setAppearance, toggleAppearance }),
    [theme, appearance, setTheme, setAppearance, toggleAppearance],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
