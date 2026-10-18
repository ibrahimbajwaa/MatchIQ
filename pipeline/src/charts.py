"""Draw the README charts from reports/metrics.json and test predictions."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
FIGS = REPORTS / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"
BLUE = "#2a78d6"
MUTED = "#b5b3ac"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": INK_2, "ytick.color": INK_2, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
})


def model_comparison(m):
    rows = m["results"]
    names = [r["model"] for r in rows]
    acc = [r["accuracy"] * 100 for r in rows]
    colors = [MUTED if n in ("Always home win", "Elo rating only") else BLUE for n in names]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = np.arange(len(names))[::-1]
    ax.barh(y, acc, color=colors, height=0.55)
    for yi, a in zip(y, acc):
        ax.text(a + 0.6, yi, f"{a:.1f}%", va="center", color=INK, fontsize=11)
    ax.set_yticks(y, names)
    ax.set_xlim(0, 65)
    ax.set_xlabel("Accuracy on 760 test matches (2023-24 and 2024-25)")
    ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
    ax.set_title("Picking W/D/L: models vs baselines (grey)", loc="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIGS / "model_comparison.png", dpi=160); plt.close(fig)


def feature_importance(m, top=10):
    imp = m["xgb_feature_importance"][:top][::-1]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh([i["feature"] for i in imp], [i["importance"] for i in imp],
            color=BLUE, height=0.55)
    ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
    ax.set_xlabel("XGBoost importance (share of total gain)")
    ax.set_title("What the model leans on: Elo dominates", loc="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIGS / "feature_importance.png", dpi=160); plt.close(fig)


def calibration(preds):
    """When the model says 60% home win, do home teams win ~60% of the time?"""
    bins = np.linspace(0, 1, 11)
    preds = preds.assign(bin=pd.cut(preds.p_home, bins, include_lowest=True))
    g = preds.groupby("bin", observed=True).agg(
        predicted=("p_home", "mean"),
        actual=("result", lambda r: (r == "H").mean()),
        n=("result", "size")).query("n >= 15")
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1.5, ls="--", label="Perfectly calibrated")
    ax.plot(g.predicted, g.actual, color=BLUE, lw=2, marker="o", ms=8,
            markeredgecolor=SURFACE, markeredgewidth=2, label="MatchIQ")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("Predicted home-win probability")
    ax.set_ylabel("Actual home-win rate")
    ax.grid(True, color=GRID); ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Are the probabilities honest?", loc="left", fontsize=13, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIGS / "calibration.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    FIGS.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((REPORTS / "metrics.json").read_text())
    model_comparison(metrics)
    feature_importance(metrics)
    calibration(pd.read_csv(REPORTS / "test_predictions.csv"))
    print("Charts saved to reports/figures/")
