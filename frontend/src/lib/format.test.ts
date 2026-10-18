import { describe, expect, it } from "vitest";
import { margin, ordinal, outcomeLabel, pct, per90, plural, pluralPosition, rawValue } from "./format";
import { smoothHistory } from "./series";
import { styleColor } from "./styles";

describe("format", () => {
  it("formats probabilities as whole percents by default", () => {
    expect(pct(0.572)).toBe("57%");
    expect(pct(0.4974, 1)).toBe("49.7%");
  });

  it("writes ordinals, including the teens", () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101, 111, 113].map(ordinal)).toEqual(
      ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "101st", "111th", "113th"]);
  });

  it("keeps per-90 numbers readable at both scales", () => {
    expect(per90(0.3072)).toBe("0.31");
    expect(per90(31.234)).toBe("31.2");
  });

  it("shows whole raw totals without decimals", () => {
    expect(rawValue(7)).toBe("7");
    expect(rawValue(7.57)).toBe("7.6");
  });

  it("labels outcomes by team", () => {
    expect(outcomeLabel("H", "Arsenal", "Chelsea")).toBe("Arsenal win");
    expect(outcomeLabel("A", "Arsenal", "Chelsea")).toBe("Chelsea win");
    expect(outcomeLabel("D", "Arsenal", "Chelsea")).toBe("Draw");
    expect(outcomeLabel(null, "Arsenal", "Chelsea")).toBe("Draw");
  });

  it("pluralises positions and counts", () => {
    expect(pluralPosition("Midfielder")).toBe("midfielders");
    expect(plural(1, "player")).toBe("1 player");
    expect(plural(1234, "player")).toBe("1,234 players");
  });

  it("measures how close a fixture is", () => {
    expect(margin({ pHome: 0.4, pAway: 0.4 })).toBe(0);
    expect(margin({ pHome: 0.2, pAway: 0.55 })).toBeCloseTo(0.35, 10);
  });
});

describe("smoothHistory", () => {
  const points = Array.from({ length: 1000 }, (_, i) => ({ date: `d${i}`, elo: 1500 + i }));

  it("never returns more points than asked and keeps both ends", () => {
    const out = smoothHistory(points, 100);
    expect(out.length).toBeLessThanOrEqual(100);
    expect(out[0]).toEqual(points[0]);
    expect(out[out.length - 1]).toEqual(points[999]);
  });

  it("leaves short series alone", () => {
    expect(smoothHistory(points.slice(0, 10), 100)).toHaveLength(10);
  });
});

describe("styleColor", () => {
  it("gives each style a stable colour by its place in the list", () => {
    const styles = ["Ball-winners", "Creators", "Goal threats"];
    expect(styleColor("Creators", styles)).toBe(styleColor("Creators", styles));
    expect(styleColor("Creators", styles)).not.toBe(styleColor("Goal threats", styles));
  });

  it("falls back to a neutral colour for a missing style", () => {
    expect(styleColor(null, ["A"])).toMatch(/^#/);
  });
});
