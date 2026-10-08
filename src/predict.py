"""Predict any Premier League fixture with the trained model.

Usage (from the src folder):
    python predict.py "Arsenal" "Tottenham"
    python predict.py --ratings          # current Elo table

Team names follow the data's spelling, e.g. "Man City", "Man United",
"Nott'm Forest", "Newcastle", "Wolves".

The prediction uses each team's state after the last match in the data.
"""
import argparse
from pathlib import Path

import joblib
import pandas as pd

from data import load_matches
from features import build_features

ROOT = Path(__file__).resolve().parent.parent


def predict(home, away):
    """Append the fixture as a fake future match, build features for all
    history, and read the last row. Features only look backwards, so the
    placeholder result on the fake row never leaks into its own features."""
    matches = load_matches()
    teams = set(matches.HomeTeam) | set(matches.AwayTeam)
    for t in (home, away):
        if t not in teams:
            raise SystemExit(f"Unknown team '{t}'. Try one of: {', '.join(sorted(teams))}")
    fake = matches.iloc[[-1]].copy()
    fake[["HomeTeam", "AwayTeam"]] = [home, away]
    fake["Date"] = matches.Date.max() + pd.Timedelta(days=1)
    df = build_features(pd.concat([matches, fake], ignore_index=True))
    row = df.iloc[[-1]]
    bundle = joblib.load(ROOT / "models" / "match_predictor.joblib")
    proba = bundle["model"].predict_proba(row[bundle["features"]])[0]
    p = dict(zip(bundle["labels"], proba))
    print(f"\n{home} vs {away}  ({bundle['name']})")
    print(f"  {home} win  {p['H']:.0%}")
    print(f"  Draw       {p['D']:.0%}")
    print(f"  {away} win  {p['A']:.0%}")
    print(f"  Elo: {home} {row.home_elo.iloc[0]:.0f}, {away} {row.away_elo.iloc[0]:.0f}")


def ratings(n=20):
    matches = load_matches()
    elo = build_features(matches).attrs["final_elo"]
    last_season = matches.season.iloc[-1]
    teams = set(matches[matches.season == last_season].HomeTeam)
    table = sorted(((t, elo[t]) for t in teams), key=lambda x: -x[1])[:n]
    print(f"\nElo ratings at the end of {last_season}:")
    for i, (t, r) in enumerate(table, 1):
        print(f"  {i:>2}. {t:<16} {r:.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("home", nargs="?")
    ap.add_argument("away", nargs="?")
    ap.add_argument("--ratings", action="store_true")
    args = ap.parse_args()
    if args.ratings:
        ratings()
    elif args.home and args.away:
        predict(args.home, args.away)
    else:
        ap.print_help()
