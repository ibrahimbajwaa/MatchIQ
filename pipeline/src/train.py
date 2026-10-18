"""Train the MatchIQ match predictor and test it against baselines.

Split is by time, never random: train on 2015-16 to 2023-24, test on the
two most recent complete seasons (2024-25 and 2025-26). The current season
is never trained or tested on; it only feeds the latest Elo and form. That mirrors real use,
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

from data import load_matches, CURRENT_SEASON
from features import build_features, FEATURES

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
MODELS = ROOT / "models"
LABELS = ["A", "D", "H"]           # class order used everywhere (alphabetical)
LABEL_TO_INT = {l: i for i, l in enumerate(LABELS)}
TEST_SEASONS = ["2024-25", "2025-26"]
VALIDATION_SEASON = "2023-24"   # used only to choose the model
WARMUP_SEASON = "2014-15"


def split(df):
    df = df[~df.season.isin([WARMUP_SEASON, CURRENT_SEASON])]
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

    # Baseline: always pick the home team; probabilities = training frequencies
    freq = np.bincount(y_tr, minlength=3) / len(y_tr)
    home_proba = np.tile(freq, (len(y_te), 1)); home_proba[:, 2] += 1e-9
    results.append(evaluate("Always home win", y_te, home_proba))

    # Three candidate models. Each entry: name -> (feature list, model factory)
    candidates = {
        "Elo rating only": (["elo_diff"], lambda: make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000))),
        "Logistic regression": (FEATURES, lambda: make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            LogisticRegression(max_iter=2000, C=0.1))),
        # Shallow trees + strong regularisation, because football is noisy
        "XGBoost": (FEATURES, lambda: XGBClassifier(
            n_estimators=300, max_depth=2, learning_rate=0.03, subsample=0.8,
            colsample_bytree=0.8, min_child_weight=5, reg_lambda=5.0,
            objective="multi:softprob", eval_metric="mlogloss", random_state=42)),
    }

    # Step 1: choose the model on a validation season the test never touches.
    # Fit on everything before VALIDATION_SEASON, score on VALIDATION_SEASON.
    fit_part = train[train.season < VALIDATION_SEASON]
    val_part = train[train.season == VALIDATION_SEASON]
    y_fit = fit_part.result.map(LABEL_TO_INT).values
    y_val = val_part.result.map(LABEL_TO_INT).values
    val_scores = {}
    for name, (feats, make) in candidates.items():
        m = make().fit(fit_part[feats], y_fit)
        val_scores[name] = log_loss(y_val, m.predict_proba(val_part[feats]), labels=[0, 1, 2])
    best_name = min(val_scores, key=val_scores.get)
    print("Validation log loss (" + VALIDATION_SEASON + "): " +
          ", ".join(f"{k} {v:.3f}" for k, v in val_scores.items()) + f"  -> chose {best_name}")

    # Step 2: refit every candidate on the full training set and score on test
    fitted, probas = {}, {}
    for name, (feats, make) in candidates.items():
        fitted[name] = make().fit(train[feats], y_tr)
        probas[name] = fitted[name].predict_proba(test[feats])
        results.append(evaluate(name, y_te, probas[name]))
    xgb = fitted["XGBoost"]

    for r in results:
        print(f"{r['model']:<22} accuracy {r['accuracy']:.1%}   log loss {r['log_loss']:.3f}")

    # Save everything the report and charts need
    REPORTS.mkdir(exist_ok=True); MODELS.mkdir(exist_ok=True)
    best_model, best_proba = fitted[best_name], probas[best_name]
    best_features = candidates[best_name][0]
    joblib.dump({"model": best_model, "name": best_name, "features": best_features,
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
        "train_seasons": [train.season.min(), train.season.max()],
        "test_seasons": TEST_SEASONS, "best_model": best_name,
        "validation_season": VALIDATION_SEASON,
        "validation_log_loss": {k: round(v, 4) for k, v in val_scores.items()},
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
