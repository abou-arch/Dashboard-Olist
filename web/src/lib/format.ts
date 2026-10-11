// Mise en forme des nombres à la française (virgule décimale, espace des milliers),
// alignée sur olist_dashboard/formatting.py.

export const NBSP = " ";

const formatters = new Map<number, Intl.NumberFormat>();

function formatter(decimals: number): Intl.NumberFormat {
  let f = formatters.get(decimals);
  if (!f) {
    f = new Intl.NumberFormat("fr-FR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    formatters.set(decimals, f);
  }
  return f;
}

/** 1234.5 -> « 1 234,5 » ; ``signed`` ajoute « + » devant une valeur positive. */
export function number(value: number, decimals = 0, signed = false): string {
  const rounded = Number(value.toFixed(decimals));
  const text = formatter(decimals).format(rounded === 0 ? 0 : value);
  return signed && rounded > 0 ? `+${text}` : text;
}

/** 1 284 -> « 1 284 », 25 400 -> « 25,4 k », 15 688 396 -> « 15,7 M ». */
export function compact(value: number): string {
  const size = Math.abs(value);
  if (size >= 1e9) return `${number(value / 1e9, 1)}${NBSP}Md`;
  if (size >= 1e6) return `${number(value / 1e6, 1)}${NBSP}M`;
  if (size >= 1e4) return `${number(value / 1e3, 1)}${NBSP}k`;
  return number(value);
}

/** Graduation d'axe : comme ``compact`` mais sans « ,0 » inutile (« 800 k »). */
export const compactTick = (value: number) => compact(value).replace(/,0(?=\D|$)/, "");

export const currency = (value: number, decimals = 0) => `R$${NBSP}${number(value, decimals)}`;
export const compactCurrency = (value: number) => `R$${NBSP}${compact(value)}`;
export const percent = (ratio: number, decimals = 1, signed = false) =>
  `${number(ratio * 100, decimals, signed)}${NBSP}%`;
export const days = (value: number, decimals = 1) => `${number(value, decimals)}${NBSP}j`;
export const score = (value: number) => `${number(value, 2)}${NBSP}/${NBSP}5`;

/** Valeur absente -> tiret, sinon ``format(value)``. */
export function orDash<T>(value: T | null | undefined, format: (v: T) => string): string {
  return value === null || value === undefined ? "–" : format(value);
}

const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

/** « 2017-01-01 » -> « janv. 2017 ». */
export function monthLabel(isoDate: string): string {
  const [year, month] = isoDate.split("-");
  return `${MONTHS[Number(month) - 1]} ${year}`;
}

/** « 2017-01-01 » -> « 01/2017 ». */
export function shortMonth(isoDate: string): string {
  const [year, month] = isoDate.split("-");
  return `${month}/${year}`;
}

/** « 2017-01-31 » -> « 31/01/2017 ». */
export function dateLabel(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}
