import type { FixtureView } from "../api/types";
import { kickoff, outcomeLabel } from "../lib/format";
import { PitchStrip } from "./PitchStrip";

/** One fixture: when, the model's three probabilities on a pitch, and the score once it has been played. */
export function FixtureRow({ fixture: f }: { fixture: FixtureView }) {
  const finished = f.result !== null;
  const hit = finished && f.predicted === f.result;
  return (
    <li className="fixture">
      <div className="fixture__when">{kickoff(f.kickoff)}</div>
      <div className="fixture__strip">
        <PitchStrip
          home={f.home.displayName}
          away={f.away.displayName}
          pHome={f.pHome}
          pDraw={f.pDraw}
          pAway={f.pAway}
          predicted={f.predicted}
          result={f.result}
          size="sm"
        />
      </div>
      <div className="fixture__result">
        {finished ? (
          <>
            <span className="fixture__score">{f.homeGoals} to {f.awayGoals}</span>
            <span className={`fixture__verdict ${hit ? "is-hit" : "is-miss"}`}>
              {hit ? "Called it" : `Picked ${outcomeLabel(f.predicted, f.home.shortName, f.away.shortName).toLowerCase()}`}
            </span>
          </>
        ) : (
          <span className="fixture__pick">Pick: {outcomeLabel(f.predicted, f.home.shortName, f.away.shortName)}</span>
        )}
      </div>
    </li>
  );
}
