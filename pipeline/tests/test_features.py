"""Tests for the feature builder. They use small made-up leagues so they run anywhere, with no data files.

The one that matters most is test_features_never_see_the_future: a model evaluated on leaky features would look
better than it is, and this is the guard against that.
"""
import numpy as np
import pandas as pd
import pytest

import features
from features import ELO_HOME_ADV, ELO_START, FEATURES, build_features


def league(results, season="2023-24", teams=("A", "B", "C", "D")):
    """Round-robin-ish fixtures with the given H/D/A results, one per match, dated a week apart."""
    rows = []
    pairs = [(h, a) for h in teams for a in teams if h != a]
    for i, res in enumerate(results):
        h, a = pairs[i % len(pairs)]
        hg, ag = {"H": (2, 0), "D": (1, 1), "A": (0, 2)}[res]
        rows.append(dict(season=season, Date=pd.Timestamp("2023-08-01") + pd.Timedelta(days=7 * i), HomeTeam=h,
                         AwayTeam=a, FTHG=hg, FTAG=ag, FTR=res, HS=10 + i, AS=8, HST=4, AST=3, HC=5, AC=4))
    return pd.DataFrame(rows)


RESULTS = list("HDAHHADHAADHDAHH")


def test_features_never_see_the_future():
    matches = league(RESULTS)
    full = build_features(matches)
    for cut in (3, 7, 12):
        partial = build_features(matches.iloc[:cut])
        pd.testing.assert_frame_equal(
            full.iloc[:cut].reset_index(drop=True), partial.reset_index(drop=True), check_exact=True, check_dtype=False)


def test_changing_a_later_result_cannot_change_an_earlier_row():
    matches = league(RESULTS)
    changed = matches.copy()
    changed.loc[10, ["FTHG", "FTAG", "FTR"]] = [0, 5, "A"]
    a, b = build_features(matches), build_features(changed)
    pd.testing.assert_frame_equal(a.iloc[:10], b.iloc[:10], check_exact=True, check_dtype=False)
    assert not a.iloc[11:].equals(b.iloc[11:]), "later rows should react to the changed result"


def test_the_label_is_the_real_result():
    matches = league(RESULTS)
    assert build_features(matches)["result"].tolist() == RESULTS


def test_everyone_starts_level_in_the_first_season():
    first = build_features(league(RESULTS)).iloc[0]
    assert first.home_elo == ELO_START and first.away_elo == ELO_START
    assert first.elo_diff == ELO_HOME_ADV
    assert np.isnan(first.home_form_pts), "no history yet means no form, not zero form"


def test_elo_is_zero_sum_within_a_season():
    matches = league(RESULTS)
    out = build_features(matches)
    assert sum(out.attrs["final_elo"].values()) == pytest.approx(ELO_START * 4)


def test_a_win_raises_the_winner_and_lowers_the_loser():
    out = build_features(league(["H", "H", "H", "H", "H", "H"]))
    first = out.iloc[0]
    winner_next = out[(out.home == first.home) | (out.away == first.home)].iloc[1]
    rating = winner_next.home_elo if winner_next.home == first.home else winner_next.away_elo
    assert rating > ELO_START
    loser_next = out[(out.home == first.away) | (out.away == first.away)].iloc[1]
    rating = loser_next.home_elo if loser_next.home == first.away else loser_next.away_elo
    assert rating < ELO_START


def test_form_averages_only_the_last_five_matches():
    from collections import deque

    def game(pts, shots=np.nan):
        return {"pts": pts, "gf": 1, "ga": 1, "shots": shots, "sot": np.nan}

    history = deque([game(p) for p in [3, 3, 3, 0, 0, 0, 1]], maxlen=features.FORM_WINDOW)
    assert features._form(history, "x")["x_pts"] == pytest.approx((3 + 0 + 0 + 0 + 1) / 5)


def test_form_skips_missing_values_instead_of_counting_them_as_zero():
    from collections import deque

    history = deque([{"pts": 3, "gf": 2, "ga": 0, "shots": np.nan, "sot": np.nan},
                     {"pts": 0, "gf": 0, "ga": 1, "shots": 12, "sot": 5}], maxlen=5)
    out = features._form(history, "x")
    assert out["x_shots"] == 12 and out["x_pts"] == 1.5
    assert np.isnan(features._form(deque(maxlen=5), "x")["x_shots"])


def test_a_newly_promoted_side_starts_below_average():
    s1 = league(RESULTS, season="2023-24", teams=("A", "B", "C", "D"))
    s2 = league(["H", "D", "A", "H"], season="2024-25", teams=("A", "B", "C", "E"))
    s2["Date"] = s2["Date"] + pd.Timedelta(days=365)
    out = build_features(pd.concat([s1, s2], ignore_index=True))
    e_row = out[(out.season == "2024-25") & ((out.home == "E") | (out.away == "E"))].iloc[0]
    e_rating = e_row.home_elo if e_row.home == "E" else e_row.away_elo
    assert e_rating == features.PROMOTED_RATING


def test_every_model_feature_is_produced():
    assert set(FEATURES) <= set(build_features(league(RESULTS)).columns)


@pytest.mark.parametrize("diff,expected", [(0, 1.0), (1, 1.0), (2, 1.5), (3, 14 / 8), (5, 2.0)])
def test_goal_difference_multiplier(diff, expected):
    assert features._goal_multiplier(diff) == expected
    assert features._goal_multiplier(-diff) == expected


def test_expected_score_is_symmetric_and_bounded():
    assert features._expected(1500, 1500) == pytest.approx(0.5)
    assert features._expected(1700, 1500) + features._expected(1500, 1700) == pytest.approx(1.0)
    assert 0 < features._expected(1000, 2000) < 0.01
