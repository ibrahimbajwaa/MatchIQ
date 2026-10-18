import { useMemo, useRef, useState } from "react";
import type { PointerEvent } from "react";
import type { MapPoint } from "../api/types";
import { styleColor } from "../lib/styles";

interface Props {
  points: MapPoint[];
  styles: string[];
  /** Style names currently shown; points of other styles are dimmed. */
  visibleStyles: ReadonlySet<string>;
  selectedId: number | null;
  /** Players to ring, e.g. the selected player's nearest neighbours. */
  neighbourIds: ReadonlySet<number>;
  onSelect: (point: MapPoint) => void;
}

const W = 900;
const H = 560;
const PAD = 28;

/**
 * Every scouted player on one plane: players near each other play alike. Axes are the first two principal components
 * of the nine per-90 stats, so they have no units; distance is the only thing that means anything.
 */
export function StyleMap({ points, styles, visibleStyles, selectedId, neighbourIds, onSelect }: Props) {
  const svg = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<MapPoint | null>(null);

  const scale = useMemo(() => {
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const sx = (v: number) => PAD + ((v - x0) / (x1 - x0 || 1)) * (W - PAD * 2);
    const sy = (v: number) => H - PAD - ((v - y0) / (y1 - y0 || 1)) * (H - PAD * 2);
    return { sx, sy };
  }, [points]);

  function nearest(e: PointerEvent<SVGSVGElement>): MapPoint | null {
    const box = svg.current?.getBoundingClientRect();
    if (!box) return null;
    const px = ((e.clientX - box.left) / box.width) * W;
    const py = ((e.clientY - box.top) / box.height) * H;
    let best: MapPoint | null = null;
    let bestD = 18 * 18; // within 18 map units
    for (const p of points) {
      if (!visibleStyles.has(p.style ?? "")) continue;
      const d = (scale.sx(p.x) - px) ** 2 + (scale.sy(p.y) - py) ** 2;
      if (d < bestD) { bestD = d; best = p; }
    }
    return best;
  }

  const selected = points.find((p) => p.id === selectedId) ?? null;
  const tip = hover ?? null;

  return (
    <div className="map">
      <svg
        ref={svg}
        className="map__svg"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Map of ${points.length} players. Players who play alike sit close together. Use the player search above the map to find someone.`}
        onPointerMove={(e) => setHover(nearest(e))}
        onPointerLeave={() => setHover(null)}
        onClick={(e) => { const p = nearest(e as unknown as PointerEvent<SVGSVGElement>); if (p) onSelect(p); }}
      >
        <rect x="1" y="1" width={W - 2} height={H - 2} className="map__field" />
        <line x1={W / 2} y1="1" x2={W / 2} y2={H - 1} className="map__mark" />
        <circle cx={W / 2} cy={H / 2} r="70" className="map__mark" />
        {points.map((p) => {
          const on = visibleStyles.has(p.style ?? "");
          return (
            <circle
              key={p.id}
              cx={scale.sx(p.x)}
              cy={scale.sy(p.y)}
              r={p.id === selectedId ? 7 : 4.2}
              fill={styleColor(p.style, styles)}
              opacity={on ? (selectedId !== null && p.id !== selectedId && !neighbourIds.has(p.id) ? 0.45 : 0.92) : 0.07}
            />
          );
        })}
        {points.filter((p) => neighbourIds.has(p.id)).map((p) => (
          <circle key={`n${p.id}`} cx={scale.sx(p.x)} cy={scale.sy(p.y)} r="9" fill="none" stroke="var(--chalk)" strokeWidth="1.5" />
        ))}
        {selected && (
          <circle cx={scale.sx(selected.x)} cy={scale.sy(selected.y)} r="12" fill="none" stroke="var(--chalk)" strokeWidth="2" />
        )}
      </svg>
      {tip && (
        <div
          className="map__tip"
          style={{ left: `${(scale.sx(tip.x) / W) * 100}%`, top: `${(scale.sy(tip.y) / H) * 100}%` }}
          role="presentation"
        >
          <strong>{tip.name}</strong>
          <span>{tip.teamShort} {tip.position.toLowerCase()}{tip.style ? `, ${tip.style.toLowerCase()}` : ""}</span>
        </div>
      )}
    </div>
  );
}
