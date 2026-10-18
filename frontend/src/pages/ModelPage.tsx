import { useModel } from "../api/hooks";
import { ErrorState, Loading } from "../components/States";
import { pct } from "../lib/format";

export function ModelPage() {
  const { data, isPending, isError, error, refetch } = useModel();
  if (isPending) return <div className="wrap"><Loading what="the model report" /></div>;
  if (isError) return <div className="wrap"><ErrorState error={error} retry={() => refetch()} /></div>;

  const chosen = data.metrics.find((m) => m.chosen);
  const baseline = data.metrics.find((m) => m.model.toLowerCase().includes("always"));
  const best = [...data.metrics].sort((a, b) => b.accuracy - a.accuracy)[0];
  const testMatches = data.seasons.reduce((n, s) => n + s.matches, 0);
  const trainMatches = Number(data.meta.trainMatches);
  const maxAcc = Math.max(...data.metrics.map((m) => m.accuracy));
  const extraMatches = chosen && best && best !== chosen ? Math.round((best.accuracy - chosen.accuracy) * testMatches) : 0;

  return (
    <div className="wrap model">
      <h1 className="page-title">How good is the model?</h1>
      {chosen && baseline && (
        <p className="lede">
          On {testMatches} matches it never saw while training, {chosen.model} picks the right result {pct(chosen.accuracy, 1)} of
          the time. Always backing the home side gets {pct(baseline.accuracy, 1)}. That gap is the whole claim: football is noisy,
          and this is a modest, honest edge rather than a crystal ball.
        </p>
      )}

      <section aria-labelledby="compare-title">
        <h2 id="compare-title">Four ways to predict a result</h2>
        <div className="table-wrap">
          <table className="table">
            <caption className="sr-only">Accuracy and log loss on the held-out matches</caption>
            <thead>
              <tr>
                <th scope="col">Approach</th>
                <th scope="col">Right result</th>
                <th scope="col" className="num">Log loss</th>
              </tr>
            </thead>
            <tbody>
              {data.metrics.map((m) => (
                <tr key={m.model} className={m.chosen ? "is-chosen" : undefined}>
                  <th scope="row">{m.model}{m.chosen && <span className="badge">in use</span>}</th>
                  <td>
                    <div className="meter">
                      <div className="meter__bar" role="img" aria-label={`${pct(m.accuracy, 1)} correct`}>
                        <span style={{ width: `${(m.accuracy / maxAcc) * 100}%` }} />
                      </div>
                      <span className="meter__num">{pct(m.accuracy, 1)}</span>
                    </div>
                  </td>
                  <td className="num">{m.logLoss.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul className="notes">
          <li><strong>Right result</strong> is how often the most likely outcome is what happened.</li>
          <li><strong>Log loss</strong> also punishes confident wrong calls and rewards honest probabilities. Lower is better, and it is what the service uses to choose a model.</li>
          {extraMatches > 0 && best && chosen && (
            <li>
              {best.model} gets {extraMatches} more {extraMatches === 1 ? "match" : "matches"} right out of {testMatches}, but its
              probabilities are worse (log loss {best.logLoss.toFixed(3)} against {chosen.logLoss.toFixed(3)}). A difference that small is within luck, so the simpler model is the one in use.
            </li>
          )}
        </ul>
      </section>

      <section aria-labelledby="season-title">
        <h2 id="season-title">Season by season</h2>
        <div className="table-wrap">
          <table className="table">
            <caption className="sr-only">Accuracy for each held-out season</caption>
            <thead>
              <tr>
                <th scope="col">Season</th>
                <th scope="col" className="num">Matches</th>
                <th scope="col" className="num">{chosen?.model ?? "Model"}</th>
                <th scope="col" className="num">Always home</th>
              </tr>
            </thead>
            <tbody>
              {data.seasons.map((s) => (
                <tr key={s.season}>
                  <th scope="row">{s.season}</th>
                  <td className="num">{s.matches}</td>
                  <td className="num strong">{pct(s.modelAccuracy, 1)}</td>
                  <td className="num">{pct(s.homeAccuracy, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {Number.isFinite(trainMatches) && (
          <p className="muted">
            Trained on {trainMatches.toLocaleString("en-GB")} earlier matches. Every feature for a match is built only from games played before it, so
            nothing from the future leaks into a prediction. A test in the repository checks that.
          </p>
        )}
      </section>
    </div>
  );
}
