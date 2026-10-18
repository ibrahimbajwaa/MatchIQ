import type { OutcomeCode } from "../api/types";
import { pct } from "../lib/format";

interface Props {
  home: string;
  away: string;
  pHome: number;
  pDraw: number;
  pAway: number;
  /** The model's pick, highlighted. */
  predicted?: OutcomeCode;
  /** What actually happened, when the match is over. */
  result?: OutcomeCode | null;
  size?: "hero" | "md" | "sm";
}

const SEGMENTS: { code: OutcomeCode; cls: string }[] = [
  { code: "H", cls: "home" },
  { code: "D", cls: "draw" },
  { code: "A", cls: "away" },
];

/**
 * A top-down pitch whose three outcome zones are sized by probability: home on the left, away on the right, the
 * draw in between. The pitch markings sit over the zones so the strip reads as a pitch first and a bar chart second.
 */
export function PitchStrip({ home, away, pHome, pDraw, pAway, predicted, result, size = "md" }: Props) {
  const p: Record<OutcomeCode, number> = { H: pHome, D: pDraw, A: pAway };
  const label = `${home} ${pct(pHome)}, draw ${pct(pDraw)}, ${away} ${pct(pAway)}`;

  return (
    <div className={`strip strip--${size}`} role="img" aria-label={label}>
      <div className="strip__pitch">
        {SEGMENTS.map(({ code, cls }) => (
          <div
            key={code}
            className={`strip__zone strip__zone--${cls}${predicted === code ? " is-pick" : ""}${result === code ? " is-result" : ""}`}
            style={{ width: `${p[code] * 100}%` }}
          >
            {p[code] >= 0.1 && <span className="strip__pct">{pct(p[code])}</span>}
          </div>
        ))}
        <svg className="strip__lines" viewBox="0 0 600 60" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
          <g fill="none" stroke="currentColor" strokeWidth="1.6" vectorEffect="non-scaling-stroke">
            <rect x="1" y="1" width="598" height="58" />
            <rect x="1" y="12" width="46" height="36" />
            <rect x="553" y="12" width="46" height="36" />
            <rect x="1" y="22" width="16" height="16" />
            <rect x="583" y="22" width="16" height="16" />
          </g>
        </svg>
      </div>
      <div className="strip__names">
        <span className="strip__name strip__name--home">{home}</span>
        <span className="strip__name strip__name--draw">Draw</span>
        <span className="strip__name strip__name--away">{away}</span>
      </div>
    </div>
  );
}
