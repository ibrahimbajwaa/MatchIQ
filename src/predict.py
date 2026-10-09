"""Predict any Premier League fixture with the trained model.

Usage (from the src folder):
    python predict.py "Arsenal" "Tottenham"
    python predict.py --ratings          # current Elo table

Team names follow the data's spelling, e.g. "Man City", "Man United",
"Nott'm Forest", "Newcastle", "Wolves".

Predictions use each team's state after the last match in the data.
The same functions power the Streamlit app (app.py).
"""
import argparse
from pathlib import Path

import joblib
import pandas as pd

from data import load_matches, load_current_season, CURRENT_SEASON
from features import build_features

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "match_predictor.joblib"


def load_model():
    return joblib.load(MODEL_PATH)


def current_teams(matches=None):
    """The 20 teams in this season's fixture list, alphabetical."""
    played, upcoming = load_current_season()
    both = pd.concat([played[["HomeTeam", "AwayTeam"]], upcoming[["HomeTeam", "AwayTeam"]]])
    return sorted(set(both.HomeTeam) | set(both.AwayTeam))


def predict_fixture(home, away, matches=None, bundle=None):
    """Return win/draw/loss probabilities plus the features behind them.

    Trick: append the fixture as a fake future match and build features for
    all history. Features only look backwards, so the placeholder result on
    the fake row never leaks into its own features.
    """
    matches = load_matches() if matches is None else matches
    bundle = load_model() if bundle is None else bundle
    teams = set(matches.HomeTeam) | set(matches.AwayTeam)
    for t in (home, away):
        if t not in teams:
            raise ValueError(f"Unknown team '{t}'")
    if home == away:
        raise ValueError("Pick two different teams")
    fake = matches.iloc[[-1]].copy()
    fake[["HomeTeam", "AwayTeam"]] = [home, away]
    fake["Date"] = matches.Date.max() + pd.Timedelta(days=1)
    row = build_features(pd.concat([matches, fake], ignore_index=True)).iloc[-1]
    proba = bundle["model"].predict_proba(row[bundle["features"]].to_frame().T)[0]
    p = dict(zip(bundle["labels"], proba))
    return {"home": home, "away": away, "model": bundle["name"],
            "p_home": float(p["H"]), "p_draw": float(p["D"]), "p_away": float(p["A"]),
            "features": row}


def recent_results(team, matches, n=5):
    """Last n results for a team, oldest first, as dicts for display."""
    games = matches[(matches.HomeTeam == team) | (matches.AwayTeam == team)].tail(n)
    out = []
    for g in games.itertuples():
        at_home = g.HomeTeam == team
        gf, ga = (g.FTHG, g.FTAG) if at_home else (g.FTAG, g.FTHG)
        res = "W" if gf > ga else "D" if gf == ga else "L"
        out.append({"date": g.Date, "opponent": g.AwayTeam if at_home else g.HomeTeam,
                    "venue": "H" if at_home else "A", "score": f"{gf}-{ga}", "result": res})
    return out


def elo_table(matches=None):
    """Current Elo rating for every team in the latest season, best first."""
    matches = load_matches() if matches is None else matches
    elo = build_features(matches).attrs["final_elo"]
    teams = current_teams()
    return sorted(((t, elo[t]) for t in teams), key=lambda x: -x[1])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("home", nargs="?")
    ap.add_argument("away", nargs="?")
    ap.add_argument("--ratings", action="store_true")
    args = ap.parse_args()
    if args.ratings:
        m = load_matches()
        print(f"\nLatest Elo ratings ({CURRENT_SEASON} teams, results to {m.Date.max():%d %b %Y}):")
        for i, (t, r) in enumerate(elo_table(m), 1):
            print(f"  {i:>2}. {t:<16} {r:.0f}")
    elif args.home and args.away:
        try:
            r = predict_fixture(args.home, args.away)
        except ValueError as e:
            raise SystemExit(str(e))
        print(f"\n{r['home']} vs {r['away']}  ({r['model']})")
        print(f"  {r['home']} win  {r['p_home']:.0%}")
        print(f"  Draw       {r['p_draw']:.0%}")
        print(f"  {r['away']} win  {r['p_away']:.0%}")
        f = r["features"]
        print(f"  Elo: {r['home']} {f.home_elo:.0f}, {r['away']} {f.away_elo:.0f}")
    else:
        ap.print_help()
