import { Link } from "react-router-dom";
import { useFixtures, useLeaderboard, useOverview } from "../api/hooks";
import { FixtureRow } from "../components/FixtureRow";
import { PitchStrip } from "../components/PitchStrip";
import { SearchBox } from "../components/SearchBox";
import { ErrorState, Loading } from "../components/States";
import { kickoff, margin, outcomeLabel, pct, per90 } from "../lib/format";

export function HomePage() {
  const overview = useOverview();
  if (overview.isPending) return <div className="wrap"><Loading what="MatchIQ" /></div>;
  if (overview.isError) return <div className="wrap"><ErrorState error={overview.error} retry={() => overview.refetch()} /></div>;
  const o = overview.data;

  return (
    <>
      {o.nextGameweek !== null ? <NextGameweek gameweek={o.nextGameweek} /> : <Header />}
      <div className="wrap split">
        <section aria-labelledby="top-title">
          <div className="section-head">
            <h2 id="top-title">Best finishers, per 90</h2>
            <Link to="/leaderboards?stat=expected_goals">See the full table</Link>
          </div>
          <TopFive />
        </section>
        <section aria-labelledby="find-title" className="aside">
          <h2 id="find-title">Find a player</h2>
          <p className="muted">See where they rank in their position and who plays like them.</p>
          <SearchBox className="search--block" placeholder="Try Saka or Haaland" />
          <div className="honest">
            <p className="honest__big">{pct(o.headline.modelAccuracy, 1)}</p>
            <p>
              of {o.headline.testMatches} unseen matches called correctly, against {pct(o.headline.baselineAccuracy, 1)} for always
              picking the home side. <Link to="/model">How it was measured</Link>
            </p>
          </div>
        </section>
      </div>
    </>
  );
}

function Header() {
  return (
    <section className="wrap hero hero--plain">
      <h1 className="display">Every Premier League player, ranked and compared.</h1>
    </section>
  );
}

function NextGameweek({ gameweek }: { gameweek: number }) {
  const { data, isPending, isError, error, refetch } = useFixtures(gameweek);
  if (isPending) return <div className="wrap"><Loading what={`gameweek ${gameweek}`} /></div>;
  if (isError) return <div className="wrap"><ErrorState error={error} retry={() => refetch()} /></div>;

  const upcoming = data.filter((f) => f.result === null);
  const closest = [...upcoming].sort((a, b) => margin(a) - margin(b))[0];
  if (!closest) return <Header />;
  const rest = data.filter((f) => f.id !== closest.id);
  const top = Math.max(closest.pHome, closest.pDraw, closest.pAway);

  return (
    <>
      <section className="wrap hero" aria-labelledby="hero-title">
        <p className="hero__kicker">Gameweek {gameweek}, closest call</p>
        <h1 id="hero-title" className="display hero__title">
          <span className="hero__side">{closest.home.displayName}</span>
          <span className="hero__side"><span className="hero__v">v</span> {closest.away.displayName}</span>
        </h1>
        <PitchStrip
          size="hero"
          home={closest.home.displayName}
          away={closest.away.displayName}
          pHome={closest.pHome}
          pDraw={closest.pDraw}
          pAway={closest.pAway}
          predicted={closest.predicted}
        />
        <p className="hero__note">
          {kickoff(closest.kickoff)}. Likeliest result: {outcomeLabel(closest.predicted, closest.home.displayName, closest.away.displayName)}, at only {pct(top)}.
          No other match this gameweek is closer.
        </p>
      </section>
      <section className="wrap" aria-labelledby="gw-title">
        <div className="section-head">
          <h2 id="gw-title">The rest of gameweek {gameweek}</h2>
          <Link to={`/fixtures?gw=${gameweek}`}>All fixtures</Link>
        </div>
        <ul className="fixtures">{rest.map((f) => <FixtureRow key={f.id} fixture={f} />)}</ul>
      </section>
    </>
  );
}

function TopFive() {
  const { data, isPending, isError, error, refetch } = useLeaderboard("expected_goals", "all", 0, 5);
  if (isPending) return <Loading what="the leaderboard" />;
  if (isError) return <ErrorState error={error} retry={() => refetch()} />;
  return (
    <ol className="toplist">
      {data.entries.map((e) => (
        <li key={e.player.id} className="toplist__row">
          <span className="toplist__rank">{e.rank}</span>
          <Link to={`/players/${e.player.id}`} className="toplist__name">{e.player.name}</Link>
          <span className="toplist__team">{e.player.teamShort}</span>
          <span className="toplist__value">{per90(e.per90)}</span>
        </li>
      ))}
    </ol>
  );
}
