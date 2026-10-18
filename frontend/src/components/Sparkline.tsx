import { useId } from "react";
import type { EloPoint } from "../api/types";
import { smoothHistory } from "../lib/series";

interface Props {
  points: EloPoint[];
  width?: number;
  height?: number;
  /** Text for assistive technology, e.g. "Arsenal rating over time, rising". */
  label: string;
}

export function Sparkline({ points, width = 140, height = 36, label }: Props) {
  const id = useId();
  const series = smoothHistory(points, 90);
  if (series.length < 2) return <span className="muted">no history</span>;

  const values = series.map((p) => p.elo);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const pad = 3;
  const x = (i: number) => pad + (i / (series.length - 1)) * (width - pad * 2);
  const y = (v: number) => height - pad - ((v - lo) / span) * (height - pad * 2);
  const line = series.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(p.elo).toFixed(1)}`).join(" ");
  const area = `${line} L${x(series.length - 1).toFixed(1)} ${height} L${x(0).toFixed(1)} ${height} Z`;
  const last = series[series.length - 1];

  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.28" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
      {last && <circle cx={x(series.length - 1)} cy={y(last.elo)} r="2.6" fill="currentColor" />}
    </svg>
  );
}
