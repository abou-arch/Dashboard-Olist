// Écarts entre la période choisie et la période précédente, comme sur les pages Streamlit.
import { number, percent } from "./format";

/** normal : une hausse est bonne ; inverse : une hausse est mauvaise ; off : neutre. */
export type DeltaMode = "normal" | "inverse" | "off";

export interface Delta {
  text: string;
  direction: "up" | "down" | "flat";
  tone: "good" | "bad" | "neutral";
}

type Value = number | null | undefined;

function build(text: string, change: number, mode: DeltaMode): Delta {
  const direction = change > 0 ? "up" : change < 0 ? "down" : "flat";
  let tone: Delta["tone"] = "neutral";
  if (mode !== "off" && direction !== "flat") {
    const good = (direction === "up") === (mode === "normal");
    tone = good ? "good" : "bad";
  }
  return { text, direction, tone };
}

/** Écart relatif : +12,3 %. */
export function relativeDelta(current: Value, previous: Value, mode: DeltaMode = "normal"): Delta | null {
  if (current == null || !previous) return null;
  const ratio = current / previous - 1;
  return build(percent(ratio, 1, true), Number((ratio * 100).toFixed(1)), mode);
}

/** Écart en points de pourcentage entre deux parts : +1,2 pt. */
export function pointDelta(current: Value, previous: Value, mode: DeltaMode = "normal"): Delta | null {
  if (current == null || previous == null) return null;
  const points = (current - previous) * 100;
  return build(`${number(points, 1, true)} pt`, Number(points.toFixed(1)), mode);
}

/** Écart absolu : +0,05 ou +1,2 j. */
export function absoluteDelta(
  current: Value, previous: Value, unit = "", decimals = 2, mode: DeltaMode = "normal",
): Delta | null {
  if (current == null || previous == null) return null;
  const change = current - previous;
  return build(`${number(change, decimals, true)}${unit}`, Number(change.toFixed(decimals)), mode);
}
