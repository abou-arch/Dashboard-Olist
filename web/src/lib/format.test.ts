import { describe, expect, it } from "vitest";

import { absoluteDelta, pointDelta, relativeDelta } from "./delta";
import { NBSP, compact, compactTick, currency, dateLabel, monthLabel, number, percent } from "./format";

// Intl sépare les milliers par une espace fine insécable (U+202F) : on la normalise.
const plain = (text: string) => text.replace(/[  ]/g, " ");

describe("format", () => {
  it("formate les nombres à la française", () => {
    expect(plain(number(1234.5, 1))).toBe("1 234,5");
    expect(number(1.234, 1, true)).toBe("+1,2");
    expect(number(-1.234, 1, true)).toMatch(/^[-−]1,2$/);
    expect(number(0.001, 1, true)).toBe("0,0");
  });

  it("abrège les grands nombres comme la version Python", () => {
    expect(plain(compact(1284))).toBe("1 284");
    expect(plain(compact(25_400))).toBe("25,4 k");
    expect(plain(compact(15_688_396))).toBe("15,7 M");
    expect(plain(compact(2.5e9))).toBe("2,5 Md");
    expect(plain(compactTick(800_000))).toBe("800 k");
    expect(plain(compactTick(1_500_000))).toBe("1,5 M");
  });

  it("formate montants, pourcentages et dates", () => {
    expect(plain(currency(1234.567, 2))).toBe("R$ 1 234,57");
    expect(percent(0.0679)).toBe(`6,8${NBSP}%`);
    expect(monthLabel("2017-11-01")).toBe("nov. 2017");
    expect(dateLabel("2017-01-31")).toBe("31/01/2017");
  });
});

describe("delta", () => {
  it("calcule un écart relatif", () => {
    expect(relativeDelta(110, 100)).toEqual({ text: `+10,0${NBSP}%`, direction: "up", tone: "good" });
    expect(relativeDelta(90, 100, "inverse")?.tone).toBe("good");
    expect(relativeDelta(110, 100, "off")?.tone).toBe("neutral");
    expect(relativeDelta(110, null)).toBeNull();
    expect(relativeDelta(110, 0)).toBeNull();
  });

  it("calcule un écart en points et en valeur absolue", () => {
    expect(pointDelta(0.08, 0.06, "inverse")).toEqual({ text: "+2,0 pt", direction: "up", tone: "bad" });
    expect(absoluteDelta(4.1, 4.1)).toEqual({ text: "0,00", direction: "flat", tone: "neutral" });
    expect(absoluteDelta(12, 12.5, " j", 1)?.text).toMatch(/^[-−]0,5 j$/);
  });
});
