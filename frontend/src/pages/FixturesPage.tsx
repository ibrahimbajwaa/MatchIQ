import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useFixtures, useOverview, usePrediction, useTeams } from "../api/hooks";
import { FixtureRow } from "../components/FixtureRow";
import { PitchStrip } from "../components/PitchStrip";
import { ErrorState, Loading } from "../components/States";
import { outcomeLabel, pct } from "../lib/format";

const LAST_GAMEWEEK = 38;

export function FixturesPage() {
  const overview = useOverview();
  const [params, setParams] = useSearchParams();
  const requested = Number(params.get("gw"));
  const gameweek = requested >= 1 && requested <= LAST_GAMEWEEK ? requested : (overview.data?.nextGameweek ?? 1);
  const fixtures = useFixtures(gameweek);
  const go = (gw: number) => setParams({ gw: String(Math.min(LAST_GAMEWEEK, Math.max(1, gw))) }, { replace: true });

  return (
    <div className="wrap">
      <h1 className="page-title">Fixtures</h1>
      <Matchup />

      <section aria-labelledby="gw-title" className="gw">
        <div className="section-head">
          <h2 id="gw-title">Gameweek {gameweek}</h2>
          <div className="pager pager--inline">
            <button type="button" className="btn" onClick={() => go(gameweek - 1)} disabled={gameweek <= 1}>Earlier</button>
            <label className="sr-only" htmlFor="gw-select">Gameweek</label>
            <select id="gw-select" className="select" value={gameweek} onChange={(e) => go(Number(e.target.value))}>
              {Array.from({ length: LAST_GAMEWEEK }, (_, i) => i + 1).map((n) => <option key={n} value={n}>Gameweek {n}</option>)}
            </select>
            <button type="button" className="btn" onClick={() => go(gameweek + 1)} disabled={gameweek >= LAST_GAMEWEEK}>Later</button>
          </div>
        </div>
        {fixtures.isPending && <Loading what="fixtures" />}
        {fixtures.isError && <ErrorState error={fixtures.error} retry={() => fixtures.refetch()} />}
        {fixtures.data && <ul className={`fixtures${fixtures.isFetching ? " is-stale" : ""}`}>{fixtures.data.map((f) => <FixtureRow key={f.id} fixture={f} />)}</ul>}
      </section>
    </div>
  );
}

/** Pick any two clubs and ask the model. Calls the same prediction endpoint the fixtures were scored with. */
function Matchup() {
  const teams = useTeams();
  const [homeId, setHomeId] = useState<number | null>(null);
  const [awayId, setAwayId] = useState<number | null>(null);
  const league = (teams.data ?? []).filter((t) => t.inLeague).sort((a, b) => a.displayName.localeCompare(b.displayName));

  // Start with the two top-rated clubs so there is something on the pitch straight away.
  useEffect(() => {
    if (homeId !== null || awayId !== null || !teams.data) return;
    const top = teams.data.filter((t) => t.inLeague).sort((a, b) => (a.eloRank ?? 99) - (b.eloRank ?? 99));
    setHomeId(top[1]?.id ?? null);
    setAwayId(top[0]?.id ?? null);
  }, [teams.data, homeId, awayId]);

  const prediction = usePrediction(homeId, awayId);
  const same = homeId !== null && homeId === awayId;
  const p = prediction.data;

  const options = (
    <>
      <option value="" disabled>Choose a club</option>
      {league.map((t) => <option key={t.id} value={t.id}>{t.displayName}</option>)}
    </>
  );

  return (
    <section aria-labelledby="matchup-title" className="matchup">
      <h2 id="matchup-title">Pick any match</h2>
      <div className="controls">
        <div className="field">
          <label htmlFor="home">Home</label>
          <select id="home" className="select" value={homeId ?? ""} onChange={(e) => setHomeId(Number(e.target.value))}>{options}</select>
        </div>
        <div className="field">
          <label htmlFor="away">Away</label>
          <select id="away" className="select" value={awayId ?? ""} onChange={(e) => setAwayId(Number(e.target.value))}>{options}</select>
        </div>
      </div>
      {same && <p className="notice" role="alert">Choose two different clubs.</p>}
      {prediction.isError && <ErrorState error={prediction.error} retry={() => prediction.refetch()} />}
      {p && !same && (
        <>
          <PitchStrip size="md" home={p.home.displayName} away={p.away.displayName} pHome={p.pHome} pDraw={p.pDraw} pAway={p.pAway} predicted={p.predicted} />
          <p className="matchup__note">
            {outcomeLabel(p.predicted, p.home.displayName, p.away.displayName)} is the likeliest result at{" "}
            {pct(Math.max(p.pHome, p.pDraw, p.pAway))}. Rating gap {Math.round(Math.abs(p.eloDiff))} points{p.eloDiff >= 0 ? " to the home side" : " to the away side"}, plus a home advantage worth {Math.round(p.homeAdvantage)}.
          </p>
        </>
      )}
    </section>
  );
}
