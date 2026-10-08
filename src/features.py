"""Turn match results into pre-match features.

The golden rule: every feature for a match is computed ONLY from games
played before kickoff. We walk through matches in date order, read each
team's current state (Elo rating, recent form), write the features, and
only then update the state with the match result. That way the model can
never peek at the result it is trying to predict (no data leakage).
"""
from collections import defaultdict, deque

import numpy as np
import pandas as pd

# --- Elo ratings -----------------------------------------------------------
ELO_START = 1500      # rating for a team's first ever match in the data
ELO_K = 20            # how far one result moves a rating
ELO_HOME_ADV = 60     # rating points the home side gets for playing at home
PROMOTED_RATING = 1420  # newly promoted sides start below average

# --- Recent form -----------------------------------------------------------
FORM_WINDOW = 5       # last N matches


def _expected(r_a, r_b):
    """Chance team A beats team B under Elo (draws count as half)."""
    return 1 / (1 + 10 ** ((r_b - r_a) / 400))


def _goal_multiplier(goal_diff):
    """Bigger wins move ratings more (standard football Elo tweak)."""
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8


def build_features(matches: pd.DataFrame) -> pd.DataFrame:
    elo = {}
    # Each team's last FORM_WINDOW matches as dicts of stats (any venue)
    recent = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    recent_home = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    recent_away = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    rows = []
    season = None

    for m in matches.itertuples(index=False):
        if m.season != season:
            season = m.season
            # Pull ratings 20% back toward average each summer (squads change)
            for t in elo:
                elo[t] = 0.8 * elo[t] + 0.2 * ELO_START

        h, a = m.HomeTeam, m.AwayTeam
        first_season = matches.season.iloc[0]
        for t in (h, a):
            if t not in elo:
                elo[t] = ELO_START if m.season == first_season else PROMOTED_RATING

        # ---------- features: state BEFORE kickoff ----------
        f = {
            "season": m.season, "date": m.Date, "home": h, "away": a,
            "home_elo": elo[h], "away_elo": elo[a],
            "elo_diff": elo[h] + ELO_HOME_ADV - elo[a],
            "elo_home_win_prob": _expected(elo[h] + ELO_HOME_ADV, elo[a]),
        }
        for side, team in (("home", h), ("away", a)):
            f.update(_form(recent[team], f"{side}_form"))
        f.update(_form(recent_home[h], "home_at_home"))
        f.update(_form(recent_away[a], "away_on_road"))
        for stat in ("pts", "gf", "ga", "shots", "sot"):
            f[f"diff_{stat}"] = f[f"home_form_{stat}"] - f[f"away_form_{stat}"]
        f["result"] = m.FTR  # H / D / A, the label
        rows.append(f)

        # ---------- update state with the result ----------
        hs = {"gf": m.FTHG, "ga": m.FTAG, "shots": m.HS, "sot": m.HST,
              "pts": 3 if m.FTR == "H" else 1 if m.FTR == "D" else 0}
        as_ = {"gf": m.FTAG, "ga": m.FTHG, "shots": m.AS, "sot": m.AST,
               "pts": 3 if m.FTR == "A" else 1 if m.FTR == "D" else 0}
        recent[h].append(hs); recent_home[h].append(hs)
        recent[a].append(as_); recent_away[a].append(as_)

        actual = 1.0 if m.FTR == "H" else 0.5 if m.FTR == "D" else 0.0
        exp = _expected(elo[h] + ELO_HOME_ADV, elo[a])
        change = ELO_K * _goal_multiplier(m.FTHG - m.FTAG) * (actual - exp)
        elo[h] += change
        elo[a] -= change

    out = pd.DataFrame(rows)
    out.attrs["final_elo"] = dict(elo)  # ratings after the last match, for predict.py
    return out


def _form(history, prefix):
    """Average stats over a team's recent matches (NaN if none yet)."""
    keys = ("pts", "gf", "ga", "shots", "sot")
    if not history:
        return {f"{prefix}_{k}": np.nan for k in keys}
    return {f"{prefix}_{k}": float(np.mean([g[k] for g in history])) for k in keys}


FEATURES = [
    "home_elo", "away_elo", "elo_diff",
    "home_form_pts", "home_form_gf", "home_form_ga", "home_form_shots", "home_form_sot",
    "away_form_pts", "away_form_gf", "away_form_ga", "away_form_shots", "away_form_sot",
    "home_at_home_pts", "home_at_home_gf", "home_at_home_ga",
    "away_on_road_pts", "away_on_road_gf", "away_on_road_ga",
    "diff_pts", "diff_gf", "diff_ga", "diff_shots", "diff_sot",
]
