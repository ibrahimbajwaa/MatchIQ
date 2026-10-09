"""Download and load Premier League match results.

Two sources:
1. Completed seasons (2014-15 to 2025-26): football-data.co.uk season files,
   mirrored on GitHub by `datasets/football-datasets`. One row per match with
   the result, shots, shots on target and corners.
2. The current season (2026-27): results so far and the remaining fixture
   list from the official Fantasy Premier League data, mirrored by
   `vaastav/Fantasy-Premier-League`. It has scores but no shot counts.
"""
import json
from pathlib import Path
import urllib.request

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BASE_URL = (
    "https://raw.githubusercontent.com/datasets/football-datasets/main/"
    "datasets/premier-league/season-{code}.csv"
)
FPL_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{season}/{file}"
CURRENT_SEASON = "2026-27"

# 2014/15 is only used to warm up Elo ratings and form; it is never trained on.
SEASONS = ["1415", "1516", "1617", "1718", "1819", "1920",
           "2021", "2122", "2223", "2324", "2425", "2526"]

# FPL team names -> the football-data.co.uk spelling used everywhere else
FPL_TO_FD = {"Man Utd": "Man United", "Spurs": "Tottenham", "Ipswich Town": "Ipswich",
             "Coventry City": "Coventry", "Hull City": "Hull", "Leicester City": "Leicester",
             "Sheffield Utd": "Sheffield United", "Luton Town": "Luton"}


def download(seasons=SEASONS, force=False):
    """Save each completed season's CSV into data/raw (skips files already there)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for code in seasons:
        path = RAW_DIR / f"season-{code}.csv"
        if path.exists() and not force:
            continue
        print(f"Downloading {code[:2]}/{code[2:]} ...")
        urllib.request.urlretrieve(BASE_URL.format(code=code), path)


FPL_API = "https://fantasy.premierleague.com/api/{endpoint}/"


def _fpl_api(endpoint):
    req = urllib.request.Request(FPL_API.format(endpoint=endpoint),
                                 headers={"User-Agent": "Mozilla/5.0 (MatchIQ student project)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def download_current():
    """Refresh the current season's results and fixtures.

    Tries, in order: the official Fantasy Premier League API (live), the
    GitHub mirror of it (updated less often), then the copy already saved in
    data/raw. Returns which source was used.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fx_path = RAW_DIR / f"fpl-{CURRENT_SEASON}-fixtures.csv"
    tm_path = RAW_DIR / f"fpl-{CURRENT_SEASON}-teams.csv"
    try:
        fixtures = pd.DataFrame(_fpl_api("fixtures"))
        teams = pd.DataFrame(_fpl_api("bootstrap-static")["teams"])
        fixtures.drop(columns=["stats"], errors="ignore").to_csv(fx_path, index=False)
        teams[["id", "name", "short_name"]].to_csv(tm_path, index=False)
        return "Official Fantasy Premier League feed"
    except Exception:
        pass
    try:
        urllib.request.urlretrieve(FPL_URL.format(season=CURRENT_SEASON, file="fixtures.csv"), fx_path)
        urllib.request.urlretrieve(FPL_URL.format(season=CURRENT_SEASON, file="teams.csv"), tm_path)
        return "Fantasy Premier League mirror on GitHub"
    except Exception as e:
        if fx_path.exists() and tm_path.exists():
            return "Saved copy"
        raise RuntimeError("Could not get current-season data and no saved copy exists") from e


def load_matches(seasons=SEASONS, include_current=True):
    """Every finished match, oldest first, with a `season` column like '2023-24'."""
    frames = []
    for code in seasons:
        df = pd.read_csv(RAW_DIR / f"season-{code}.csv")
        df["season"] = f"20{code[:2]}-{code[2:]}"
        frames.append(df)
    if include_current:
        played, _ = load_current_season()
        frames.append(played)
    matches = pd.concat(frames, ignore_index=True)
    matches["Date"] = pd.to_datetime(matches["Date"], utc=True).dt.tz_localize(None)
    keep = ["season", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
            "HS", "AS", "HST", "AST", "HC", "AC"]
    return matches[keep].sort_values("Date", kind="stable").reset_index(drop=True)


def load_current_season():
    """Return (finished matches, upcoming fixtures) for the current season."""
    fx = pd.read_csv(RAW_DIR / f"fpl-{CURRENT_SEASON}-fixtures.csv")
    teams = pd.read_csv(RAW_DIR / f"fpl-{CURRENT_SEASON}-teams.csv")
    name = {r.id: FPL_TO_FD.get(r.name, r.name) for r in teams.itertuples()}
    fx["HomeTeam"] = fx.team_h.map(name)
    fx["AwayTeam"] = fx.team_a.map(name)
    fx["Date"] = pd.to_datetime(fx.kickoff_time, utc=True).dt.tz_localize(None)
    done = fx[fx.finished.astype(str).str.lower() == "true"].copy()
    done["FTHG"] = done.team_h_score.astype(int)
    done["FTAG"] = done.team_a_score.astype(int)
    done["FTR"] = done.apply(lambda r: "H" if r.FTHG > r.FTAG else "A" if r.FTHG < r.FTAG else "D", axis=1)
    for col in ("HS", "AS", "HST", "AST", "HC", "AC"):
        done[col] = float("nan")
    done["season"] = CURRENT_SEASON
    upcoming = fx[fx.finished.astype(str).str.lower() != "true"][
        ["event", "Date", "HomeTeam", "AwayTeam"]].rename(columns={"event": "gameweek"})
    upcoming = upcoming.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return done, upcoming


if __name__ == "__main__":
    download()
    print("Current season from:", download_current())
    m = load_matches()
    _, up = load_current_season()
    print(f"{len(m)} finished matches from {m.season.iloc[0]} to {m.season.iloc[-1]}")
    print(f"{(m.season == CURRENT_SEASON).sum()} played so far in {CURRENT_SEASON}, "
          f"{len(up)} fixtures still to play")
