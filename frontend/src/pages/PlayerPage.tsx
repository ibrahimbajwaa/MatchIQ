import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { usePlayer, useScoutMap, useSimilar } from "../api/hooks";
import { StatRow } from "../components/StatRow";
import { ErrorState, Loading } from "../components/States";
import { pluralPosition } from "../lib/format";
import { styleColor } from "../lib/styles";

export function PlayerPage() {
  const id = Number(useParams().id);
  const profile = usePlayer(id);
  const map = useScoutMap();
  const [samePosition, setSamePosition] = useState(true);
  const similar = useSimilar(Number.isInteger(id) ? id : null, samePosition);

  if (profile.isPending) return <div className="wrap"><Loading what="the player" /></div>;
  if (profile.isError) return <div className="wrap"><ErrorState error={profile.error} retry={() => profile.refetch()} /></div>;
  const { player, stats } = profile.data;
  const styles = map.data?.styles ?? [];

  return (
    <div className="wrap player">
      <header className="player__head">
        <h1 className="display player__name">{player.name}</h1>
        <p className="player__full">{player.fullName !== player.name ? `${player.fullName}. ` : ""}{player.teamName}</p>
        <ul className="chips">
          <li className="chip">{player.position}</li>
          {player.style && (
            <li className="chip" style={{ ["--dot" as string]: styleColor(player.style, styles) }}>
              <span className="chip__dot" aria-hidden="true" />{player.style}
            </li>
          )}
          <li className="chip">{player.minutes.toLocaleString("en-GB")} minutes</li>
        </ul>
      </header>

      <div className="player__grid">
        <section aria-labelledby="stats-title">
          <h2 id="stats-title">Against other {pluralPosition(player.position)}</h2>
          <p className="muted">Each bar shows the share of players in the same position this player out-produces, per 90 minutes. The mark is the median.</p>
          <div className="stats">
            {stats.map((s) => <StatRow key={s.key} stat={s} position={player.position} />)}
          </div>
        </section>

        <section aria-labelledby="similar-title" className="aside">
          <h2 id="similar-title">Plays like</h2>
          <div className="seg" role="group" aria-label="Which players to compare with">
            <button type="button" className={`seg__btn${samePosition ? " is-on" : ""}`} aria-pressed={samePosition} onClick={() => setSamePosition(true)}>
              Same position
            </button>
            <button type="button" className={`seg__btn${!samePosition ? " is-on" : ""}`} aria-pressed={!samePosition} onClick={() => setSamePosition(false)}>
              Anyone
            </button>
          </div>
          {similar.isPending && <Loading what="similar players" />}
          {similar.isError && <ErrorState error={similar.error} retry={() => similar.refetch()} />}
          {similar.data && (
            <ol className="similar">
              {similar.data.map((s) => (
                <li key={s.player.id} className="similar__row">
                  <div className="similar__who">
                    <Link to={`/players/${s.player.id}`} className="player-link">{s.player.name}</Link>
                    <span className="sub">{s.player.teamShort}, {s.player.position.toLowerCase()}</span>
                  </div>
                  <div className="similar__score" title="Cosine similarity of the nine per-90 stats, standardised">
                    <span className="similar__bar" aria-hidden="true"><span style={{ width: `${Math.max(0, s.similarity) * 100}%` }} /></span>
                    <span>{s.similarity.toFixed(2)}</span>
                  </div>
                </li>
              ))}
            </ol>
          )}
          <Link className="btn btn--ghost" to={`/scout?player=${player.id}`}>Show on the scout map</Link>
        </section>
      </div>
    </div>
  );
}
