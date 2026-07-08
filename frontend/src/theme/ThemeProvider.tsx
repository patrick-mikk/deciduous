import * as React from "react";

export type Theme = "light" | "dark";
const STORAGE_KEY = "deciduous:theme";

function getSystemTheme(): Theme {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : null;
}

interface ThemeContextValue {
  /** The theme currently painted on <html data-theme>. */
  theme: Theme;
  /** True once the user has explicitly picked a theme (vs. following the OS). */
  isExplicit: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  /** Forget the explicit choice and follow the OS preference again. */
  followSystem: () => void;
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

/**
 * Writes `data-theme` on <html>, persists an explicit user choice to
 * localStorage, and otherwise follows `prefers-color-scheme` live via
 * matchMedia. index.html stamps an initial guess before React boots (to
 * avoid a flash); this provider reconciles with that on mount.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(() => getStoredTheme() ?? getSystemTheme());
  const [isExplicit, setIsExplicit] = React.useState<boolean>(() => getStoredTheme() !== null);

  // Apply to <html> whenever theme changes.
  React.useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Follow OS changes live, but only while the user hasn't made an explicit choice.
  React.useEffect(() => {
    if (isExplicit || !window.matchMedia) return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => setThemeState(e.matches ? "dark" : "light");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [isExplicit]);

  const setTheme = React.useCallback((next: Theme) => {
    setThemeState(next);
    setIsExplicit(true);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const toggleTheme = React.useCallback(() => {
    setThemeState((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      window.localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
    setIsExplicit(true);
  }, []);

  const followSystem = React.useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setIsExplicit(false);
    setThemeState(getSystemTheme());
  }, []);

  const value = React.useMemo(
    () => ({ theme, isExplicit, setTheme, toggleTheme, followSystem }),
    [theme, isExplicit, setTheme, toggleTheme, followSystem],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme() must be used within <ThemeProvider>");
  return ctx;
}
