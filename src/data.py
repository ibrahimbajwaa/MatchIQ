"""Download and load Premier League match results.

Source: football-data.co.uk season files, mirrored on GitHub by the
`datasets/football-datasets` project. One row per match with the result,
shots, shots on target, corners, fouls and cards.
"""
from pathlib import Path
import urllib.request

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BASE_URL = (
    "https://raw.githubusercontent.com/datasets/football-datasets/main/"
    "datasets/premier-league/season-{code}.csv"
)
# 2014/15 is only used to warm up Elo ratings and form; it is never trained on.
SEASONS = ["1415", "1516", "1617", "1718", "1819", "1920",
           "2021", "2122", "2223", "2324", "2425"]


def download(seasons=SEASONS, force=False):
    """Save each season's CSV into data/raw (skips files already there)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for code in seasons:
        path = RAW_DIR / f"season-{code}.csv"
        if path.exists() and not force:
            continue
        print(f"Downloading {code[:2]}/{code[2:]} ...")
        urllib.request.urlretrieve(BASE_URL.format(code=code), path)


def load_matches(seasons=SEASONS):
    """Return every match, oldest first, with a `season` column like '2023-24'."""
    frames = []
    for code in seasons:
        df = pd.read_csv(RAW_DIR / f"season-{code}.csv")
        df["season"] = f"20{code[:2]}-{code[2:]}"
        frames.append(df)
    matches = pd.concat(frames, ignore_index=True)
    matches["Date"] = pd.to_datetime(matches["Date"])
    keep = ["season", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
            "HS", "AS", "HST", "AST", "HC", "AC"]
    return matches[keep].sort_values("Date", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    download()
    m = load_matches()
    print(f"{len(m)} matches from {m.season.iloc[0]} to {m.season.iloc[-1]}")
