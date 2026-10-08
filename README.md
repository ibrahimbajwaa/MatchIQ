# MatchIQ

AI football analytics for the Premier League. MatchIQ predicts match results, finds statistically similar players, and answers questions in plain English.

| Module | What it does | Status |
|---|---|---|
| **Match Predictor** | Win / draw / loss probabilities for any fixture | ✅ Done |
| **Player Scout** | "Find players like Saka" similarity search + playing-style clusters | 🔜 Next |
| **Ask MatchIQ** | Chatbot that answers from the predictor and scout | 🔜 Planned |

---

## Match Predictor

### Results

Trained on 3,040 matches (2015-16 to 2022-23), tested on the 760 matches of the two most recent seasons (2023-24 and 2024-25), which the model never saw during training.

![Model comparison](reports/figures/model_comparison.png)

| Model | Accuracy | Log loss (lower is better) |
|---|---|---|
| Always pick the home team (baseline) | 43.4% | 1.067 |
| Elo rating only (baseline) | 54.7% | 0.959 |
| Logistic regression, 24 features | 54.9% | 0.962 |
| XGBoost, 24 features | 55.3% | 0.976 |

**What I found**

- **The model beats the naive home-team baseline by about 12 points** (55% vs 43%).
- **Elo ratings carry most of the signal.** Adding 23 form features (recent points, goals, shots, shots on target, home/away splits) on top of Elo barely improved accuracy and slightly worsened log loss. A well-tuned team-strength rating is very hard to beat with box-score stats. That matches what published football models find.
- **The probabilities are well calibrated.** When the model gives a home side a 60% chance, home sides in that bucket won about 60% of the time:

![Calibration](reports/figures/calibration.png)

- **Draws are the weak spot.** Draws were 23% of test matches, but the model almost never picks one (6 of 760), because a draw is rarely the single most likely outcome. It still assigns sensible draw probabilities; it just doesn't choose them.
- **Results vary by season:** 57.9% in 2023-24 and 51.8% in 2024-25. Home advantage was unusually weak in 2024-25 (home teams won only 40.8% of matches).

![Feature importance](reports/figures/feature_importance.png)

### How it works

1. **Data:** match results and stats (goals, shots, shots on target) for 11 Premier League seasons from [football-data.co.uk](https://www.football-data.co.uk), via the [datasets/football-datasets](https://github.com/datasets/football-datasets) mirror.
2. **No data leakage:** features are built by walking through matches in date order. Each match's features use only games played before kickoff, and the team's state is updated only after the features are recorded.
3. **Elo ratings:** each team has a strength rating that rises after wins and falls after losses. Bigger wins move it more, home sides get a 60-point boost, ratings regress 20% toward average each summer, and promoted teams start below average. Settings were checked on held-out seasons (2021-23) before testing.
4. **Form features:** last-5-match averages of points, goals for and against, shots and shots on target. Separate home-only and away-only form, plus home-minus-away differences.
5. **Time-based split:** train on older seasons, test on the newest. A random split would let the model "see the future".
6. **Models:** regularised logistic regression and a shallow XGBoost, scored on accuracy and log loss. The model with the lower log loss is saved.

### Run it

```bash
pip install -r requirements.txt
cd src
python data.py        # download 11 seasons into data/raw
python train.py       # build features, train, evaluate -> reports/metrics.json
python charts.py      # draw the charts in reports/figures
python predict.py "Arsenal" "Chelsea"
python predict.py --ratings
```

Team names follow the dataset's spelling: `Man City`, `Man United`, `Nott'm Forest`, `Newcastle`, `Wolves`.

### Limitations and next steps

- Data ends with 2024-25, so predictions reflect each team's state at that point. Next step: add 2025-26 results as they come in.
- Compare against bookmaker odds, the toughest public benchmark.
- Add expected goals (xG) features, which predict future results better than raw shots.
- Try a Poisson goals model (Dixon-Coles) to predict draws better.

## Project structure

```
matchiq/
├── data/raw/            season CSVs (downloaded by data.py)
├── models/              saved match predictor
├── reports/
│   ├── metrics.json     every number in this README
│   ├── test_predictions.csv
│   └── figures/
└── src/
    ├── data.py          download + load matches
    ├── features.py      Elo ratings and form features (leak-free)
    ├── train.py         train, compare to baselines, save
    ├── charts.py        README charts
    └── predict.py       predict a fixture / show Elo table
```

Built by Ibrahim Bajwa · Computer Science, University of Calgary
