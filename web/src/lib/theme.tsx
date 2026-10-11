// Couleurs des graphiques, lues dans les variables CSS (styles.css) : le thème
// sombre est défini à un seul endroit.
import { useMemo } from "react";

export interface Tokens {
  card: string;
  text: string;
  text2: string;
  muted: string;
  grid: string;
  baseline: string;
  accent: string;
  accentStrong: string;
  accentWash: string;
  series: string[];
  status: { delivered: string; transit: string; pending: string; canceled: string };
  sequential: string[];
  font: string;
}

export function readTokens(): Tokens {
  const style = getComputedStyle(document.documentElement);
  const v = (name: string) => style.getPropertyValue(name).trim();
  return {
    card: v("--card"),
    text: v("--text"),
    text2: v("--text-2"),
    muted: v("--muted"),
    grid: v("--grid"),
    baseline: v("--baseline"),
    accent: v("--accent"),
    accentStrong: v("--accent-strong"),
    accentWash: v("--accent-wash"),
    series: [v("--series-1"), v("--series-2"), v("--series-3")],
    status: {
      delivered: v("--status-delivered"),
      transit: v("--status-transit"),
      pending: v("--status-pending"),
      canceled: v("--status-canceled"),
    },
    sequential: [0, 1, 2, 3, 4, 5].map((i) => v(`--seq-${i}`)),
    font: v("--font"),
  };
}

export function useTokens(): Tokens {
  return useMemo(() => readTokens(), []);
}
