import { toLatinDigits } from "./digits";

/** Format an integer/count for Persian UI with mandatory Latin digits. */
export function formatCount(value: number): string {
  const formatted = new Intl.NumberFormat("fa-IR", {
    numberingSystem: "latn",
    maximumFractionDigits: 0,
  }).format(value);
  return toLatinDigits(formatted);
}

/** Format a percentage with Latin digits. */
export function formatPercent(value: number, fractionDigits = 0): string {
  const formatted = new Intl.NumberFormat("fa-IR", {
    numberingSystem: "latn",
    style: "percent",
    maximumFractionDigits: fractionDigits,
  }).format(value);
  return toLatinDigits(formatted);
}
