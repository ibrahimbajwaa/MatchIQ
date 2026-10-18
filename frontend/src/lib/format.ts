import type { FixtureView, OutcomeCode } from "../api/types";

export const pct = (p: number, digits = 0): string => `${(p * 100).toFixed(digits)}%`;

/** 1 -> "1st", 22 -> "22nd", 113 -> "113th". */
export function ordinal(n: number): string {
  const suffixes = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${suffixes[(v - 20) % 10] ?? suffixes[v] ?? "th"}`;
}

/** Per-90 values are small for some stats (0.04 goals) and large for others (31 threat); keep them readable. */
export function per90(value: number): string {
  const abs = Math.abs(value);
  return value.toFixed(abs >= 10 ? 1 : 2);
}

export function rawValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export const pluralPosition = (position: string): string => `${position.toLowerCase()}s`;

export function outcomeLabel(code: OutcomeCode | string | null, home: string, away: string): string {
  if (code === "H") return `${home} win`;
  if (code === "A") return `${away} win`;
  return "Draw";
}

const kickoffFormat = new Intl.DateTimeFormat("en-GB", {
  weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
});
export const kickoff = (iso: string): string => kickoffFormat.format(new Date(iso));

const dayFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
export const longDate = (isoDate: string): string => dayFormat.format(new Date(`${isoDate}T00:00:00Z`));

export const isFinished = (fixture: Pick<FixtureView, "result">): boolean => fixture.result !== null;

/** How far from a coin-flip a fixture is: 0 is a dead heat between the two sides. */
export const margin = (f: Pick<FixtureView, "pHome" | "pAway">): number => Math.abs(f.pHome - f.pAway);

export function plural(n: number, word: string): string {
  return `${n.toLocaleString("en-GB")} ${word}${n === 1 ? "" : "s"}`;
}
