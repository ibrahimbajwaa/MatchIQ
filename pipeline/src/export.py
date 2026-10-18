"""Export the pipeline's results for the backend and the frontend.

The Python side does the data science (Elo ratings, the match model, player
stats, similarity inputs, playing-style clusters). The Java service serves it.
This script is the hand-off between the two:

    pipeline/out/dataset.json     everything, as plain JSON (also used by the frontend mock server)
    backend/.../elo_logit.properties   the match model's coefficients (logistic regression on Elo difference)
    backend/.../R__seed_data.sql       the same dataset as a Flyway repeatable migration (re-runs when it changes)
    backend/src/test/resources/golden  Python's answers (probabilities, similar players, leaderboards) that the
                                       Java code is tested against, so the two languages can never drift apart

Run from the repo root or from this folder:
    python pipeline/src/export.py

Nothing here touches the network: it reads the data already saved in data/raw.
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import scout
from data import CURRENT_SEASON, FPL_TO_FD, RAW_DIR, load_current_season, load_matches
from features import ELO_HOME_ADV, build_features
from predict import current_teams, load_model

warnings.filterwarnings("ignore", category=UserWarning)

PIPELINE = Path(__file__).resolve().parent.parent
REPO = PIPELINE.parent
OUT = PIPELINE / "out"
BACKEND = REPO / "backend"
SEED_SQL = BACKEND / "src/main/resources/db/migration/R__seed_data.sql"
MODEL_COPY = BACKEND / "src/main/resources/model/elo_logit.properties"
GOLDEN_DIR = BACKEND / "src/test/resources/golden"

def r4(v):
    """The single rounding rule for per-90 values, so the seed data and every golden file agree."""
    return round(float(v), 4)


HISTORY_FROM = "2022-23"   # Elo timeline starts here (older seasons add noise, not insight)

DISPLAY_NAMES = {
    "Man City": "Manchester City", "Man United": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Newcastle": "Newcastle United",
    "Tottenham": "Tottenham Hotspur", "West Ham": "West Ham United",
    "Wolves": "Wolverhampton Wanderers", "Brighton": "Brighton & Hove Albion",
    "Leeds": "Leeds United", "Hull": "Hull City", "Ipswich": "Ipswich Town",
    "Coventry": "Coventry City", "Leicester": "Leicester City",
    "Sheffield United": "Sheffield United", "Luton": "Luton Town",
}

STAT_DESCRIPTIONS = {
    "goals_scored": "Goals scored.",
    "expected_goals": "Quality of the chances a player took: the goals an average finisher would score from them.",
    "assists": "Passes that led directly to a goal.",
    "expected_assists": "Quality of the chances a player created for others.",
    "threat": "Fantasy Premier League's index of how often a player is in shooting positions.",
    "creativity": "Fantasy Premier League's index of how often a player creates chances.",
    "tackles": "Tackles made.",
    "clearances_blocks_interceptions": "Defensive actions that stop an attack: clearances, blocks and interceptions.",
    "recoveries": "Times a player won the ball back when it was loose or with the opposition.",
}


# --------------------------------------------------------------------------- model
def export_model(bundle):
    """Pull the logistic regression apart so another language can run it."""
    pipe = bundle["model"]
    assert bundle["features"] == ["elo_diff"], "the Java port assumes the Elo-only model"
    scaler = pipe.named_steps["standardscaler"]
    lr = pipe.named_steps["logisticregression"]
    assert list(lr.classes_) == [0, 1, 2], "class order must be A, D, H"
    return {
        "name": bundle["name"],
        "feature": "elo_diff",
        "homeAdvantage": ELO_HOME_ADV,
        "labels": bundle["labels"],            # ["A", "D", "H"]
        "mean": float(scaler.mean_[0]),
        "scale": float(scaler.scale_[0]),
        "coef": [float(c) for c in lr.coef_[:, 0]],
        "intercept": [float(b) for b in lr.intercept_],
    }


def make_predictor(pipe):
    def predict(elo_diff):
        X = pd.DataFrame({"elo_diff": np.asarray(elo_diff, dtype=float)})
        P = pipe.predict_proba(X)
        return P[:, 2], P[:, 1], P[:, 0]       # home, draw, away
    return predict


# --------------------------------------------------------------------------- dataset
def build_dataset():
    bundle = load_model()
    predict = make_predictor(bundle["model"])
    matches = load_matches()
    feats = build_features(matches)
    final_elo = feats.attrs["final_elo"]
    last_date = matches.Date.max()

    # ---- players & scouting inputs
    players = scout.load_players()
    sc = scout.Scout(players)
    style_name = sc.style_names()

    # ---- teams: this season's 20, plus last season's clubs (that's where the scouting stats come from)
    cur = current_teams()
    prev = sorted(set(players.team))
    all_teams = sorted(set(cur) | set(prev))
    missing = [t for t in all_teams if t not in final_elo]
    assert not missing, f"no Elo rating for {missing}"
    short = {}
    for season_file in ("fpl-2025-26-teams.csv", f"fpl-{CURRENT_SEASON}-teams.csv"):
        for r in pd.read_csv(RAW_DIR / season_file).itertuples():
            short[FPL_TO_FD.get(r.name, r.name)] = r.short_name
    rank = {t: i + 1 for i, t in enumerate(sorted(cur, key=lambda t: -final_elo[t]))}
    team_id = {t: i + 1 for i, t in enumerate(all_teams)}
    teams = [{
        "id": team_id[t], "name": t, "displayName": DISPLAY_NAMES.get(t, t),
        "shortName": short.get(t, t[:3].upper()),
        "elo": round(final_elo[t], 2), "eloRank": rank.get(t), "inLeague": t in cur,
    } for t in all_teams]

    # ---- Elo timeline for this season's teams: rating going into each match, plus "now"
    elo_points = []
    recent = feats[feats.season >= HISTORY_FROM]
    for t in cur:
        h = recent[recent.home == t][["date", "home_elo"]].rename(columns={"home_elo": "elo"})
        a = recent[recent.away == t][["date", "away_elo"]].rename(columns={"away_elo": "elo"})
        series = pd.concat([h, a]).sort_values("date", kind="stable")
        pts = [(d, e) for d, e in zip(series.date, series.elo)]
        pts.append((last_date, final_elo[t]))
        for n, (d, e) in enumerate(pts, 1):
            elo_points.append({"teamId": team_id[t], "pointNo": n,
                               "matchDate": d.strftime("%Y-%m-%d"), "elo": round(float(e), 2)})

    # ---- players, per-stat rows
    player_rows, stat_rows = [], []
    for i, p in players.iterrows():
        player_rows.append({
            "id": int(p["id"]), "name": p["name"], "fullName": p["full_name"],
            "teamId": team_id[p["team"]], "position": p["position"], "minutes": int(p["minutes"]),
            "style": style_name[int(sc.cluster[i])],
            "pcaX": round(float(sc.xy[i, 0]), 4), "pcaY": round(float(sc.xy[i, 1]), 4),
        })
        for j, (col, _label) in enumerate(scout.STATS):
            feat = f"{col}_p90"
            stat_rows.append({
                "playerId": int(p["id"]), "statKey": col,
                "raw": round(float(pd.to_numeric(p[col], errors="coerce") or 0), 2),
                "per90": r4(p[feat]),
                "percentile": round(float(sc.pct.loc[i, feat]), 1),
                "zscore": float(sc.X[i, j]),
            })
    stat_defs = [{"key": c, "label": label, "description": STAT_DESCRIPTIONS[c], "sortOrder": n}
                 for n, (c, label) in enumerate(scout.STATS, 1)]

    # ---- fixtures: upcoming ones predicted from today's ratings, finished ones from pre-match ratings
    fx = pd.read_csv(RAW_DIR / f"fpl-{CURRENT_SEASON}-fixtures.csv")
    names = {r.id: FPL_TO_FD.get(r.name, r.name)
             for r in pd.read_csv(RAW_DIR / f"fpl-{CURRENT_SEASON}-teams.csv").itertuples()}
    fx["home"], fx["away"] = fx.team_h.map(names), fx.team_a.map(names)
    fx["kickoff"] = pd.to_datetime(fx.kickoff_time, utc=True).dt.tz_localize(None)
    fx = fx.dropna(subset=["kickoff", "event"]).sort_values(["kickoff", "id"])
    done_mask = fx.finished.astype(str).str.lower() == "true"

    pre = feats[feats.season == CURRENT_SEASON][["date", "home", "away", "elo_diff"]]
    fx = fx.merge(pre, how="left", left_on=["kickoff", "home", "away"], right_on=["date", "home", "away"])
    upcoming_diff = (fx.home.map(final_elo) + ELO_HOME_ADV - fx.away.map(final_elo))
    fx["elo_diff"] = np.where(done_mask.values, fx.elo_diff, upcoming_diff)
    assert not fx.elo_diff.isna().any(), "could not line up a finished fixture with its pre-match rating"
    p_home, p_draw, p_away = predict(fx.elo_diff.values)
    labels = np.array(["A", "D", "H"])
    fixtures = []
    for n, r in enumerate(fx.itertuples()):
        probs = np.array([p_away[n], p_draw[n], p_home[n]])
        finished = bool(done_mask.iloc[n])
        result = None
        if finished:
            result = "H" if r.team_h_score > r.team_a_score else "A" if r.team_h_score < r.team_a_score else "D"
        fixtures.append({
            "id": int(r.id), "gameweek": int(r.event),
            "kickoff": r.kickoff.strftime("%Y-%m-%d %H:%M:%S+00"),
            "homeTeamId": team_id[r.home], "awayTeamId": team_id[r.away],
            "status": "FINISHED" if finished else "UPCOMING",
            "homeGoals": int(r.team_h_score) if finished else None,
            "awayGoals": int(r.team_a_score) if finished else None,
            "pHome": round(float(p_home[n]), 4), "pDraw": round(float(p_draw[n]), 4),
            "pAway": round(float(p_away[n]), 4),
            "predicted": str(labels[probs.argmax()]), "result": result,
        })

    # ---- model report card (held-out seasons) from reports/metrics.json
    metrics = json.loads((PIPELINE / "reports" / "metrics.json").read_text())
    model_metrics = [{"model": r["model"], "accuracy": r["accuracy"], "logLoss": r["log_loss"],
                      "chosen": r["model"] == metrics["best_model"]} for r in metrics["results"]]
    model_seasons = [{"season": s["season"], "matches": s["matches"],
                      "modelAccuracy": s["model_accuracy"], "homeAccuracy": s["home_accuracy"]}
                     for s in metrics["per_season"]]

    return {
        "meta": {
            "dataThrough": last_date.strftime("%Y-%m-%d"), "currentSeason": CURRENT_SEASON,
            "scoutSeason": scout.SEASON, "scoutMinMinutes": scout.MIN_MINUTES,
            "trainMatches": metrics["train_matches"], "testMatches": metrics["test_matches"],
            "trainSeasons": metrics["train_seasons"], "testSeasons": metrics["test_seasons"],
            "validationSeason": metrics["validation_season"], "chosenModel": metrics["best_model"],
        },
        "teams": teams, "eloPoints": elo_points, "players": player_rows, "playerStats": stat_rows,
        "statDefs": stat_defs, "fixtures": fixtures,
        "modelMetrics": model_metrics, "modelSeasons": model_seasons,
    }, bundle, predict, final_elo, sc, players


# --------------------------------------------------------------------------- SQL
def q(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return repr(float(v))
    return "'" + str(v).replace("'", "''") + "'"


def insert(table, columns, rows, chunk=400):
    out = []
    for k in range(0, len(rows), chunk):
        values = ",\n".join("  (" + ", ".join(q(row[c]) for c in columns) + ")" for row in rows[k:k + chunk])
        out.append(f"INSERT INTO {table} ({', '.join(c for c in columns)}) VALUES\n{values};")
    return "\n".join(out)


def to_sql(ds):
    parts = [
        "-- GENERATED by pipeline/src/export.py. Do not edit by hand.",
        "-- Repeatable Flyway migration: re-runs whenever this file changes, replacing all data below.",
        f"-- Data through {ds['meta']['dataThrough']}, current season {ds['meta']['currentSeason']}.",
        "",
        "TRUNCATE TABLE player_stat, player, team_elo_point, fixture, stat_def,"
        " model_metric, model_season, team, dataset_meta RESTART IDENTITY CASCADE;",
        "",
        insert("dataset_meta", ["k", "v"], [{"k": k, "v": json.dumps(v)} for k, v in ds["meta"].items()]),
        insert("team", ["id", "name", "display_name", "short_name", "elo", "elo_rank", "in_league"],
               [{"id": t["id"], "name": t["name"], "display_name": t["displayName"], "short_name": t["shortName"],
                 "elo": t["elo"], "elo_rank": t["eloRank"], "in_league": t["inLeague"]} for t in ds["teams"]]),
        insert("team_elo_point", ["team_id", "point_no", "match_date", "elo"],
               [{"team_id": p["teamId"], "point_no": p["pointNo"], "match_date": p["matchDate"], "elo": p["elo"]}
                for p in ds["eloPoints"]]),
        insert("stat_def", ["stat_key", "label", "description", "sort_order"],
               [{"stat_key": s["key"], "label": s["label"], "description": s["description"],
                 "sort_order": s["sortOrder"]} for s in ds["statDefs"]]),
        insert("player", ["id", "name", "full_name", "team_id", "position", "minutes", "style", "pca_x", "pca_y"],
               [{"id": p["id"], "name": p["name"], "full_name": p["fullName"], "team_id": p["teamId"],
                 "position": p["position"], "minutes": p["minutes"], "style": p["style"],
                 "pca_x": p["pcaX"], "pca_y": p["pcaY"]} for p in ds["players"]]),
        insert("player_stat", ["player_id", "stat_key", "raw_value", "per90", "percentile", "zscore"],
               [{"player_id": s["playerId"], "stat_key": s["statKey"], "raw_value": s["raw"], "per90": s["per90"],
                 "percentile": s["percentile"], "zscore": s["zscore"]} for s in ds["playerStats"]]),
        insert("fixture", ["id", "gameweek", "kickoff", "home_team_id", "away_team_id", "status", "home_goals",
                           "away_goals", "p_home", "p_draw", "p_away", "predicted", "result"],
               [{"id": f["id"], "gameweek": f["gameweek"], "kickoff": f["kickoff"], "home_team_id": f["homeTeamId"],
                 "away_team_id": f["awayTeamId"], "status": f["status"], "home_goals": f["homeGoals"],
                 "away_goals": f["awayGoals"], "p_home": f["pHome"], "p_draw": f["pDraw"], "p_away": f["pAway"],
                 "predicted": f["predicted"], "result": f["result"]} for f in ds["fixtures"]]),
        insert("model_metric", ["model", "accuracy", "log_loss", "chosen"],
               [{"model": m["model"], "accuracy": m["accuracy"], "log_loss": m["logLoss"], "chosen": m["chosen"]}
                for m in ds["modelMetrics"]]),
        insert("model_season", ["season", "matches", "model_accuracy", "home_accuracy"],
               [{"season": s["season"], "matches": s["matches"], "model_accuracy": s["modelAccuracy"],
                 "home_accuracy": s["homeAccuracy"]} for s in ds["modelSeasons"]]),
        "",
    ]
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- goldens
def model_properties(model):
    return "\n".join([
        "# GENERATED by pipeline/src/export.py. Multinomial logistic regression on the Elo difference.",
        f"name={model['name']}",
        f"homeAdvantage={model['homeAdvantage']!r}",
        f"mean={model['mean']!r}",
        f"scale={model['scale']!r}",
        "labels=" + ",".join(model["labels"]),
        "coef=" + ",".join(repr(c) for c in model["coef"]),
        "intercept=" + ",".join(repr(b) for b in model["intercept"]),
        "",
    ])


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(",".join(header) + "\n" + "\n".join(",".join(str(c) for c in r) for r in rows) + "\n")


def write_goldens(ds, sc, players, final_elo, predict):
    keys = [c for c, _ in scout.STATS]
    feats = [f"{c}_p90" for c in keys]

    # 1. Win/draw/loss probabilities for real and extreme pairings
    name_of = {t["id"]: t["name"] for t in ds["teams"]}
    pairs = [(final_elo[name_of[f["homeTeamId"]]], final_elo[name_of[f["awayTeamId"]]])
             for f in [f for f in ds["fixtures"] if f["status"] == "UPCOMING"][:12]]
    pairs += [(1800.0, 1300.0), (1300.0, 1800.0), (1500.0, 1500.0), (1693.4, 1415.2), (1440.0, 1675.9)]
    ph, pdr, pa = predict([h + ELO_HOME_ADV - a for h, a in pairs])
    write_csv(GOLDEN_DIR / "predictions.csv", ["homeElo", "awayElo", "pHome", "pDraw", "pAway"],
              [(repr(h), repr(a), repr(float(ph[i])), repr(float(pdr[i])), repr(float(pa[i])))
               for i, (h, a) in enumerate(pairs)])

    # 2. Every player's vectors: per-90 values (for leaderboards) and z-scores (for similarity)
    write_csv(GOLDEN_DIR / "players.csv",
              ["id", "position"] + [f"p90_{k}" for k in keys] + [f"z_{k}" for k in keys],
              [(int(p["id"]), p["position"]) + tuple(repr(r4(p[f])) for f in feats)
               + tuple(repr(float(sc.X[i, j])) for j in range(len(keys)))
               for i, p in players.iterrows()])

    # 3. Nearest neighbours (cosine similarity) for 8 players, with and without the same-position filter
    picks = players.sort_values(["minutes", "id"], ascending=[False, True]).index[::40][:8]
    rows = []
    for i in picks:
        for same in (False, True):
            top = sc.similar(players.name[i], n=10, same_position=same)
            for rank, (_, r) in enumerate(top.iterrows(), 1):
                rows.append((int(players.id[i]), str(same).lower(), rank, int(r["id"]), repr(float(r["similarity"]))))
    write_csv(GOLDEN_DIR / "similar.csv", ["playerId", "samePosition", "rank", "neighbourId", "similarity"], rows)

    # 4. Leaderboards: per-90 value, ties broken by higher player id first (same as Redis' reverse order on
    #    zero-padded ids), competition ranking (1, 2, 2, 4)
    rows = []
    for k, f in zip(keys, feats):
        for scope in ("all", "Defender", "Midfielder", "Forward"):
            board = players if scope == "all" else players[players.position == scope]
            board = board.assign(score=board[f].map(r4))
            for pos, (_, r) in enumerate(board.sort_values(["score", "id"], ascending=[False, False]).head(15).iterrows()):
                rank = 1 + int((board.score > r["score"]).sum())      # competition rank: ties share a rank
                rows.append((k, scope, pos + 1, rank, int(r["id"]), repr(float(r["score"]))))
    write_csv(GOLDEN_DIR / "leaderboards.csv", ["stat", "scope", "position", "rank", "playerId", "score"], rows)
    return len(pairs), len(picks) * 20, len(rows)


# --------------------------------------------------------------------------- main
def main():
    ds, bundle, predict, final_elo, sc, players = build_dataset()
    model = export_model(bundle)

    OUT.mkdir(exist_ok=True)
    (OUT / "dataset.json").write_text(json.dumps(ds, indent=1))
    for path, text in ((SEED_SQL, to_sql(ds)), (MODEL_COPY, model_properties(model))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    n_pred, n_sim, n_lb = write_goldens(ds, sc, players, final_elo, predict)

    up = sum(f["status"] == "UPCOMING" for f in ds["fixtures"])
    print(f"teams {len(ds['teams'])} ({sum(t['inLeague'] for t in ds['teams'])} in the league), "
          f"players {len(ds['players'])}, player stats {len(ds['playerStats'])}, "
          f"Elo points {len(ds['eloPoints'])}")
    print(f"fixtures {len(ds['fixtures'])}: {up} upcoming, {len(ds['fixtures']) - up} finished")
    print(f"model {model['name']}: mean {model['mean']:.3f}, scale {model['scale']:.3f}, "
          f"coef {np.round(model['coef'], 4).tolist()}, intercept {np.round(model['intercept'], 4).tolist()}")
    print(f"goldens: {n_pred} predictions, {n_sim} similarity rows, {n_lb} leaderboard rows")
    print(f"wrote {OUT.relative_to(REPO)}/, {SEED_SQL.relative_to(REPO)} ({SEED_SQL.stat().st_size // 1024} KB), "
          f"{MODEL_COPY.relative_to(REPO)}, {GOLDEN_DIR.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
