import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useScoutMap, useSimilar } from "../api/hooks";
import type { MapPoint } from "../api/types";
import { SearchBox } from "../components/SearchBox";
import { StyleMap } from "../components/StyleMap";
import { ErrorState, Loading } from "../components/States";
import { styleColor } from "../lib/styles";

export function ScoutPage() {
  const { data, isPending, isError, error, refetch } = useScoutMap();
  const [params, setParams] = useSearchParams();
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());
  const selectedId = Number(params.get("player")) || null;
  const similar = useSimilar(selectedId, false, 6);

  const visible = useMemo(() => new Set((data?.styles ?? []).filter((s) => !hidden.has(s))), [data, hidden]);
  const neighbours = useMemo(() => new Set((similar.data ?? []).map((s) => s.player.id)), [similar.data]);

  if (isPending) return <div className="wrap"><Loading what="the scout map" /></div>;
  if (isError) return <div className="wrap"><ErrorState error={error} retry={() => refetch()} /></div>;

  const select = (id: number | null) => {
    const p = new URLSearchParams(params);
    id === null ? p.delete("player") : p.set("player", String(id));
    setParams(p, { replace: true });
  };
  const toggle = (style: string) =>
    setHidden((prev) => { const n = new Set(prev); n.has(style) ? n.delete(style) : n.add(style); return n; });
  const selected: MapPoint | undefined = data.points.find((p) => p.id === selectedId);

  return (
    <div className="wrap">
      <h1 className="page-title">Scout map</h1>
      <p className="lede">
        {data.points.length} players placed by how they play, not by how well. Two players close together produce similar
        numbers across all nine statistics. The axes have no units.
      </p>

      <div className="controls">
        <div className="field">
          <span className="field__label" id="find-label">Find a player on the map</span>
          <SearchBox label="Find a player on the map" placeholder="Search players" onSelect={(p) => select(p.id)} />
        </div>
        <ul className="legend" aria-label="Playing styles. Select one to hide or show it.">
          {data.styles.map((s) => (
            <li key={s}>
              <button type="button" className={`legend__btn${hidden.has(s) ? " is-off" : ""}`} aria-pressed={!hidden.has(s)} onClick={() => toggle(s)}>
                <span className="legend__dot" style={{ background: styleColor(s, data.styles) }} aria-hidden="true" />
                {s}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="scout">
        <StyleMap
          points={data.points}
          styles={data.styles}
          visibleStyles={visible}
          selectedId={selectedId}
          neighbourIds={neighbours}
          onSelect={(p) => select(p.id)}
        />
        <aside className="scout__panel" aria-live="polite">
          {selected ? (
            <>
              <h2 className="display">{selected.name}</h2>
              <p className="muted">{selected.teamShort}, {selected.position.toLowerCase()}{selected.style ? `, ${selected.style.toLowerCase()}` : ""}</p>
              <p className="panel-label">Closest on the map</p>
              <ol className="similar">
                {similar.data?.map((s) => (
                  <li key={s.player.id} className="similar__row">
                    <button type="button" className="link-btn" onClick={() => select(s.player.id)}>{s.player.name}</button>
                    <span className="sub">{s.player.teamShort}</span>
                  </li>
                ))}
              </ol>
              <Link className="btn" to={`/players/${selected.id}`}>Open profile</Link>
              <button type="button" className="btn btn--ghost" onClick={() => select(null)}>Clear</button>
            </>
          ) : (
            <p className="muted">Select a dot, or search for a player, to see who they sit next to.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
