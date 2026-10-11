// Thème clair / sombre : suit le système par défaut, peut être forcé (mémorisé
// dans le navigateur). Les graphiques lisent les couleurs dans les variables CSS.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemePreference = "system" | "light" | "dark";
type Resolved = "light" | "dark";

const STORAGE_KEY = "olist-theme";
const media = () => window.matchMedia("(prefers-color-scheme: dark)");

function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // Stockage indisponible (navigation privée…) : on suit le système.
  }
  return "system";
}

interface ThemeState {
  preference: ThemePreference;
  resolved: Resolved;
  setPreference: (p: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeState | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(readPreference);
  const [systemDark, setSystemDark] = useState(() => media().matches);

  useEffect(() => {
    const query = media();
    const update = () => setSystemDark(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (preference === "system") delete root.dataset.theme;
    else root.dataset.theme = preference;
    try {
      if (preference === "system") localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, preference);
    } catch {
      // Préférence non mémorisée : sans conséquence.
    }
  }, [preference]);

  const resolved: Resolved = preference === "system" ? (systemDark ? "dark" : "light") : preference;
  const value = useMemo(() => ({ preference, resolved, setPreference }), [preference, resolved]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeState {
  const state = useContext(ThemeContext);
  if (!state) throw new Error("useTheme doit être utilisé dans <ThemeProvider>.");
  return state;
}

/** Couleurs des graphiques, lues dans les variables CSS du thème actif. */
export interface Tokens {
  surface: string;
  text: string;
  text2: string;
  muted: string;
  grid: string;
  baseline: string;
  accent: string;
  accentWash: string;
  series: string[];
  sequential: string[];
  font: string;
}

export function readTokens(): Tokens {
  const style = getComputedStyle(document.documentElement);
  const v = (name: string) => style.getPropertyValue(name).trim();
  return {
    surface: v("--surface"),
    text: v("--text"),
    text2: v("--text-2"),
    muted: v("--muted"),
    grid: v("--grid"),
    baseline: v("--baseline"),
    accent: v("--accent"),
    accentWash: v("--accent-wash"),
    series: [v("--series-1"), v("--series-2"), v("--series-3")],
    sequential: [0, 1, 2, 3, 4, 5].map((i) => v(`--seq-${i}`)),
    font: v("--font"),
  };
}

/** Jetons du thème actif, recalculés à chaque changement de thème. */
export function useTokens(): Tokens {
  const { resolved } = useTheme();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => readTokens(), [resolved]);
}
