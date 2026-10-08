"""Train the MatchIQ match predictor and test it against baselines.

Split is by time, never random: train on 2015-16 to 2022-23, test on the
two most recent seasons (2023-24 and 2024-25). That mirrors real use,
where you only ever know the past when predicting the next game.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier

from data import load_matches
from features import build_features, FEATURES

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
MODELS = ROOT / "models"
LABELS = ["A", "D", "H"]           # class order used everywhere (alphabetical)
LABEL_TO_INT = {l: i for i, l in enumerate(LABELS)}
TEST_SEASONS = ["2023-24", "2024-25"]
WARMUP_SEASON = "2014-15"


def split(df):
    df = df[df.season != WARMUP_SEASON]
    train = df[~df.season.isin(TEST_SEASONS)]
    test = df[df.season.isin(TEST_SEASONS)]
    return train, test


def evaluate(name, y_true, proba):
    pred = proba.argmax(axis=1)
    return {
        "model": name,
        "accuracy": round(accuracy_score(y_true, pred), 4),
        "log_loss": round(log_loss(y_true, proba, labels=[0, 1, 2]), 4),
        "pred_draw_share": round(float((pred == 1).mean()), 4),
    }


def main():
    matches = load_matches()
    df = build_features(matches)
    train, test = split(df)
    X_tr, X_te = train[FEATURES], test[FEATURES]
    y_tr = train.result.map(LABEL_TO_INT).values
    y_te = test.result.map(LABEL_TO_INT).values
    print(f"Train: {len(train)} matches ({train.season.min()} to {train.season.max()})")
    print(f"Test:  {len(test)} matches ({', '.join(TEST_SEASONS)})")

    results = []

    # Baseline 1: always pick the home team; probabilities = training frequencies
    freq = np.bincount(y_tr, minlength=3) / len(y_tr)
    home_proba = np.tile(freq, (len(y_te), 1))
    home_proba_pick = home_proba.copy(); home_proba_pick[:, 2] += 1e-9
    results.append(evaluate("Always home win", y_te, home_proba_pick))

    # Baseline 2: Elo ratings alone
    elo_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    elo_model.fit(train[["elo_diff"]], y_tr)
    results.append(evaluate("Elo rating only", y_te, elo_model.predict_proba(test[["elo_diff"]])))

    # Model 1: logistic regression on every feature
    logreg = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                           LogisticRegression(max_iter=2000, C=0.1))
    logreg.fit(X_tr, y_tr)
    lr_proba = logreg.predict_proba(X_te)
    results.append(evaluate("Logistic regression", y_te, lr_proba))

    # Model 2: XGBoost (shallow trees + strong regularisation; football is noisy)
    xgb = XGBClassifier(n_estimators=300, max_depth=2, learning_rate=0.03,
                        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
                        reg_lambda=5.0, objective="multi:softprob",
                        eval_metric="mlogloss", random_state=42)
    xgb.fit(X_tr, y_tr)
    xgb_proba = xgb.predict_proba(X_te)
    results.append(evaluate("XGBoost", y_te, xgb_proba))

    for r in results:
        print(f"{r['model']:<22} accuracy {r['accuracy']:.1%}   log loss {r['log_loss']:.3f}")

    # Save everything the report and charts need
    REPORTS.mkdir(exist_ok=True); MODELS.mkdir(exist_ok=True)
    best_name, best_model, best_proba = min(
        [("Logistic regression", logreg, lr_proba), ("XGBoost", xgb, xgb_proba)],
        key=lambda t: log_loss(y_te, t[2], labels=[0, 1, 2]))
    joblib.dump({"model": best_model, "name": best_name, "features": FEATURES,
                 "labels": LABELS}, MODELS / "match_predictor.joblib")

    per_season = []
    for s in TEST_SEASONS:
        mask = (test.season == s).values
        per_season.append({
            "season": s,
            "matches": int(mask.sum()),
            "model_accuracy": round(accuracy_score(y_te[mask], best_proba[mask].argmax(1)), 4),
            "home_accuracy": round(float((y_te[mask] == 2).mean()), 4),
        })

    preds = test[["season", "date", "home", "away", "result"]].copy()
    preds[["p_away", "p_draw", "p_home"]] = best_proba
    preds["predicted"] = [LABELS[i] for i in best_proba.argmax(1)]
    preds.to_csv(REPORTS / "test_predictions.csv", index=False)

    importance = sorted(zip(FEATURES, xgb.feature_importances_.tolist()),
                        key=lambda t: -t[1])
    out = {
        "train_matches": len(train), "test_matches": len(test),
        "test_seasons": TEST_SEASONS, "best_model": best_name,
        "results": results, "per_season": per_season,
        "confusion_matrix": confusion_matrix(y_te, best_proba.argmax(1), labels=[0, 1, 2]).tolist(),
        "confusion_labels": LABELS,
        "test_outcome_share": {l: round(float((y_te == i).mean()), 4) for i, l in enumerate(LABELS)},
        "xgb_feature_importance": [{"feature": f, "importance": round(v, 4)} for f, v in importance],
    }
    (REPORTS / "metrics.json").write_text(json.dumps(out, indent=2))
    print(f"\nBest model: {best_name}. Saved to models/ and reports/.")


if __name__ == "__main__":
    main()
