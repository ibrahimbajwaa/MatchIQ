import { useRatings } from "../api/hooks";
import { Sparkline } from "../components/Sparkline";
import { ErrorState, Loading } from "../components/States";

export function TeamsPage() {
  const { data, isPending, isError, error, refetch } = useRatings();
  if (isPending) return <div className="wrap"><Loading what="team ratings" /></div>;
  if (isError) return <div className="wrap"><ErrorState error={error} retry={() => refetch()} /></div>;

  const teams = data.filter((t) => t.inLeague).sort((a, b) => (a.eloRank ?? 99) - (b.eloRank ?? 99));

  return (
    <div className="wrap">
      <h1 className="page-title">Team ratings</h1>
      <p className="lede">
        Elo ratings: every club starts level, beating a strong side moves a rating more than beating a weak one, and the
        gap between two ratings is what the match model turns into win, draw and loss probabilities.
      </p>
      <div className="table-wrap">
        <table className="table">
          <caption className="sr-only">Clubs ranked by Elo rating</caption>
          <thead>
            <tr>
              <th scope="col" className="num">Rank</th>
              <th scope="col">Club</th>
              <th scope="col" className="num">Rating</th>
              <th scope="col" className="hide-sm">History</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((t) => (
              <tr key={t.id}>
                <td className="num rank">{t.eloRank}</td>
                <td><span className="strong">{t.displayName}</span><span className="sub">{t.shortName}</span></td>
                <td className="num strong">{Math.round(t.elo)}</td>
                <td className="hide-sm spark-cell">
                  <Sparkline points={t.history} label={`${t.displayName} rating over time`} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
