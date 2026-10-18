import type { StatLine } from "../api/types";
import { ordinal, per90, pluralPosition, rawValue } from "../lib/format";

interface Props {
  stat: StatLine;
  position: string;
}

/** One stat as a percentile bar: how this player compares with everyone else in the same position. */
export function StatRow({ stat, position }: Props) {
  const percentile = Math.round(stat.percentile);
  const rankText =
    stat.positionRank !== null && stat.positionTotal !== null
      ? `${ordinal(stat.positionRank)} of ${stat.positionTotal} ${pluralPosition(position)}`
      : `${ordinal(percentile)} percentile`;

  return (
    <div className="stat">
      <div className="stat__head">
        <span className="stat__label" title={stat.description}>{stat.label}</span>
        <span className="stat__value">{per90(stat.per90)}<span className="stat__unit"> per 90</span></span>
      </div>
      <div className="stat__bar" role="img" aria-label={`${stat.label}: ${percentile}th percentile, ${rankText}`}>
        <div className="stat__fill" style={{ width: `${Math.max(stat.percentile, 1.5)}%` }} data-tier={tier(percentile)} />
        <div className="stat__tick" style={{ left: "50%" }} aria-hidden="true" />
      </div>
      <div className="stat__foot">
        <span>{rankText}</span>
        <span>{rawValue(stat.raw)} this season</span>
      </div>
    </div>
  );
}

const tier = (percentile: number): "elite" | "good" | "mid" | "low" =>
  percentile >= 90 ? "elite" : percentile >= 70 ? "good" : percentile >= 40 ? "mid" : "low";
