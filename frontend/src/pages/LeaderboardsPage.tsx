import { Link, useSearchParams } from "react-router-dom";
import { useLeaderboard, useStats } from "../api/hooks";
import type { LeaderboardEntry, Scope } from "../api/types";
import { ErrorState, Loading } from "../components/States";
import { per90, rawValue } from "../lib/format";

const SCOPES: { value: Scope; label: string }[] = [
  { value: "all", label: "Everyone" },
  { value: "Defender", label: "Defenders" },
  { value: "Midfielder", label: "Midfielders" },
  { value: "Forward", label: "Forwards" },
];
const PAGE = 25;

export function LeaderboardsPage() {
  const [params, setParams] = useSearchParams();
  const stats = useStats();
  const stat = params.get("stat") ?? stats.data?.[0]?.key ?? "goals_scored";
  const scope = (SCOPES.find((s) => s.value === params.get("scope"))?.value ?? "all") as Scope;
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const board = useLeaderboard(stat, scope, offset, PAGE);

  const update = (next: Record<string, string | null>) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) v === null ? p.delete(k) : p.set(k, v);
    setParams(p, { replace: true });
  };
  const def = stats.data?.find((s) => s.key === stat);

  return (
    <div className="wrap">
      <h1 className="page-title">Leaderboards</h1>
      <p className="lede">Ranked per 90 minutes, so a player who got fewer minutes isn't punished. Only players with at least 900 minutes last season are ranked.</p>

      <div className="controls">
        <div className="field">
          <label htmlFor="stat">Statistic</label>
          <select id="stat" className="select" value={stat} onChange={(e) => update({ stat: e.target.value, offset: null })}>
            {stats.data?.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>
        <div className="seg" role="group" aria-label="Position">
          {SCOPES.map((s) => (
            <button
              key={s.value}
              type="button"
              className={`seg__btn${scope === s.value ? " is-on" : ""}`}
              aria-pressed={scope === s.value}
              onClick={() => update({ scope: s.value === "all" ? null : s.value, offset: null })}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
      {def && <p className="stat-note">{def.description}</p>}

      {board.isPending && <Loading what="the leaderboard" />}
      {board.isError && <ErrorState error={board.error} retry={() => board.refetch()} />}
      {board.data && (
        <>
          <div className={`table-wrap${board.isFetching ? " is-stale" : ""}`}>
            <table className="table">
              <caption className="sr-only">{board.data.label}, {scope === "all" ? "all positions" : `${scope.toLowerCase()}s`}</caption>
              <thead>
                <tr>
                  <th scope="col" className="num">Rank</th>
                  <th scope="col">Player</th>
                  <th scope="col" className="hide-sm">Style</th>
                  <th scope="col" className="num">Per 90</th>
                  <th scope="col" className="num hide-sm">Season total</th>
                </tr>
              </thead>
              <tbody>
                {board.data.entries.map((e, i, all) => (
                  <Row key={e.player.id} entry={e} tied={isTied(all, i)} />
                ))}
              </tbody>
            </table>
          </div>
          <nav className="pager" aria-label="Pages">
            <button type="button" className="btn" disabled={offset === 0} onClick={() => update({ offset: String(Math.max(0, offset - PAGE)) })}>Previous</button>
            <span>{board.data.total === 0 ? "No players" : `${offset + 1} to ${Math.min(offset + PAGE, board.data.total)} of ${board.data.total}`}</span>
            <button type="button" className="btn" disabled={offset + PAGE >= board.data.total} onClick={() => update({ offset: String(offset + PAGE) })}>Next</button>
          </nav>
        </>
      )}
    </div>
  );
}

function isTied(all: LeaderboardEntry[], i: number): boolean {
  const rank = all[i]?.rank;
  return rank === all[i - 1]?.rank || rank === all[i + 1]?.rank;
}

function Row({ entry: e, tied }: { entry: LeaderboardEntry; tied: boolean }) {
  return (
    <tr>
      <td className="num rank" title={tied ? "Level with another player" : undefined}>{tied ? "=" : ""}{e.rank}</td>
      <td>
        <Link to={`/players/${e.player.id}`} className="player-link">{e.player.name}</Link>
        <span className="sub">{e.player.teamShort}, {e.player.position.toLowerCase()}</span>
      </td>
      <td className="hide-sm">{e.player.style ?? ""}</td>
      <td className="num strong">{per90(e.per90)}</td>
      <td className="num hide-sm">{rawValue(e.raw)}</td>
    </tr>
  );
}
