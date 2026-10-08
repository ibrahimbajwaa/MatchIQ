"""MatchIQ web app.  Run locally with:  streamlit run app.py"""
import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from data import load_matches, download  # noqa: E402
from predict import (load_model, predict_fixture, recent_results,  # noqa: E402
                     current_teams, elo_table)

st.set_page_config(page_title="MatchIQ", page_icon="⚽", layout="centered")

st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 820px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.mq-eyebrow {font-size: .78rem; letter-spacing: .12em; text-transform: uppercase;
             color: #5d6b65; font-weight: 600; margin-bottom: .2rem;}
.mq-bar {display: flex; height: 46px; border-radius: 8px; overflow: hidden;
         margin: .4rem 0 .3rem; font-weight: 600; font-size: .95rem;}
.mq-bar div {display: flex; align-items: center; justify-content: center;
             color: #fff; min-width: 0; white-space: nowrap; overflow: hidden;}
.mq-h {background: #1d6b52;} .mq-d {background: #8c958f;} .mq-a {background: #2457a6;}
.mq-legend {display: flex; justify-content: space-between; font-size: .9rem; color: #3b4641;}
.mq-chip {display: inline-flex; width: 26px; height: 26px; border-radius: 6px;
          align-items: center; justify-content: center; font-weight: 700;
          font-size: .8rem; color: #fff; margin-right: 4px;}
.mq-W {background: #1d6b52;} .mq-D {background: #8c958f;} .mq-L {background: #b23b3b;}
.mq-note {font-size: .85rem; color: #5d6b65;}
</style>
""", unsafe_allow_html=True)


# ---------- cached data ----------
@st.cache_data(show_spinner="Loading 11 seasons of matches…")
def get_matches():
    download()  # no-op when the CSVs are already in data/raw
    return load_matches()


@st.cache_resource
def get_model():
    return load_model()


@st.cache_data(show_spinner=False)
def get_prediction(home, away):
    r = predict_fixture(home, away, get_matches(), get_model())
    f = r.pop("features")
    r["f"] = f.to_dict()
    return r


@st.cache_data
def get_metrics():
    return json.loads((ROOT / "reports" / "metrics.json").read_text())


matches = get_matches()
TEAMS = current_teams(matches)
LAST_SEASON = matches.season.iloc[-1]


def form_chips(team):
    games = recent_results(team, matches)
    chips = "".join(f'<span class="mq-chip mq-{g["result"]}" '
                    f'title="{g["venue"]} vs {g["opponent"]} {g["score"]}">{g["result"]}</span>'
                    for g in games)
    return chips, games


# ---------- pages ----------
def predictor_page():
    st.markdown('<div class="mq-eyebrow">Match Predictor</div>', unsafe_allow_html=True)
    st.title("Who wins?")
    st.caption(f"Pick a fixture. MatchIQ uses Elo ratings and recent form as of the end of {LAST_SEASON}.")

    c1, c2 = st.columns(2)
    home = c1.selectbox("Home team", TEAMS, index=TEAMS.index("Arsenal") if "Arsenal" in TEAMS else 0)
    away_opts = [t for t in TEAMS if t != home]
    default_away = "Chelsea" if "Chelsea" in away_opts else away_opts[0]
    away = c2.selectbox("Away team", away_opts, index=away_opts.index(default_away))

    r = get_prediction(home, away)
    ph, pd_, pa = r["p_home"], r["p_draw"], r["p_away"]

    def seg(cls, p, label):
        text = f"{p:.0%}" if p >= 0.07 else ""
        return f'<div class="{cls}" style="width:{p*100:.2f}%" title="{label} {p:.1%}">{text}</div>'

    st.markdown(
        f'<div class="mq-bar">{seg("mq-h", ph, home)}{seg("mq-d", pd_, "Draw")}{seg("mq-a", pa, away)}</div>',
        unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{home} win", f"{ph:.0%}")
    m2.metric("Draw", f"{pd_:.0%}")
    m3.metric(f"{away} win", f"{pa:.0%}")

    st.subheader("Why the model thinks this")
    f = r["f"]
    gap = f["home_elo"] - f["away_elo"]
    stronger = home if gap > 0 else away
    st.write(
        f"**Elo ratings:** {home} {f['home_elo']:.0f} vs {away} {f['away_elo']:.0f}. "
        f"{stronger} is rated {abs(gap):.0f} points higher, and {home} also gets a "
        f"home-advantage boost. Elo is the model's single strongest signal."
    )

    left, right = st.columns(2)
    for col, team in ((left, home), (right, away)):
        chips, games = form_chips(team)
        col.markdown(f"**{team}**, last 5 (oldest → newest)")
        col.markdown(chips, unsafe_allow_html=True)
        col.markdown(
            '<div class="mq-note">' +
            "<br>".join(f'{g["venue"]} vs {g["opponent"]} · {g["score"]}' for g in games) +
            "</div>", unsafe_allow_html=True)

    stats = pd.DataFrame({
        "Stat (avg, last 5)": ["Points", "Goals scored", "Goals conceded", "Shots", "Shots on target"],
        home: [f["home_form_pts"], f["home_form_gf"], f["home_form_ga"], f["home_form_shots"], f["home_form_sot"]],
        away: [f["away_form_pts"], f["away_form_gf"], f["away_form_ga"], f["away_form_shots"], f["away_form_sot"]],
    })
    st.dataframe(stats.style.format({home: "{:.1f}", away: "{:.1f}"}),
                 hide_index=True, width="stretch")
    st.caption(f"Model: {r['model']}. The model rarely picks a draw outright, but the draw "
               "probability above is still meaningful.")


def rankings_page():
    st.markdown('<div class="mq-eyebrow">Power Rankings</div>', unsafe_allow_html=True)
    st.title(f"Elo table, end of {LAST_SEASON}")
    st.caption("Each team's strength rating. Wins against strong teams raise it most; "
               "1500 is roughly an average Premier League side.")
    table = pd.DataFrame(elo_table(matches), columns=["Team", "Elo"])
    table.index = range(1, len(table) + 1)
    table["Elo"] = table["Elo"].round(0).astype(int)
    chart_df = table.assign(base=1500,
                            side=lambda d: (d.Elo >= 1500).map({True: "Above average",
                                                                 False: "Below average"}))
    bars = alt.Chart(chart_df).mark_bar(height=16).encode(
        x=alt.X("Elo:Q", scale=alt.Scale(domain=[1200, 1800]),
                title="Elo rating (bars start at 1500, an average side)"),
        x2="base:Q",
        y=alt.Y("Team:N", sort=alt.EncodingSortField("Elo", order="descending"),
                title=None, axis=alt.Axis(labelLimit=180, labelFontSize=12)),
        color=alt.Color("side:N", scale=alt.Scale(domain=["Above average", "Below average"],
                                                   range=["#1d6b52", "#b23b3b"]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=["Team", "Elo"])
    st.altair_chart(bars.properties(height=560), width="stretch")
    st.dataframe(table, width="stretch")


def performance_page():
    m = get_metrics()
    st.markdown('<div class="mq-eyebrow">Model Performance</div>', unsafe_allow_html=True)
    st.title("How good is it?")
    st.write(f"Trained on {m['train_matches']:,} matches (2015-16 to 2022-23) and tested on "
             f"{m['test_matches']} matches from {' and '.join(m['test_seasons'])} that it never saw.")
    best = next(x for x in m["results"] if x["model"] == m["best_model"])
    home = next(x for x in m["results"] if x["model"] == "Always home win")
    c1, c2, c3 = st.columns(3)
    c1.metric("MatchIQ accuracy", f"{best['accuracy']:.1%}",
              f"+{(best['accuracy'] - home['accuracy']) * 100:.1f} pts vs home baseline")
    c2.metric("Always-home baseline", f"{home['accuracy']:.1%}")
    c3.metric("Test matches", m["test_matches"])

    res = pd.DataFrame(m["results"]).rename(columns={
        "model": "Model", "accuracy": "Accuracy", "log_loss": "Log loss (lower = better)",
        "pred_draw_share": "Share predicted as draw"})
    st.dataframe(res.style.format({"Accuracy": "{:.1%}", "Share predicted as draw": "{:.1%}",
                                   "Log loss (lower = better)": "{:.3f}"}),
                 hide_index=True, width="stretch")

    figs = ROOT / "reports" / "figures"
    st.image(str(figs / "model_comparison.png"))
    st.subheader("Are the probabilities honest?")
    st.write("When the model gives a home side a 60% chance, home sides in that group won about 60% "
             "of the time. The closer the line is to the diagonal, the more you can trust the numbers.")
    st.image(str(figs / "calibration.png"), width=460)
    st.subheader("What it learned")
    st.write("Elo ratings carry most of the signal. Recent-form stats add very little on top, "
             "which matches what published football models find.")
    st.image(str(figs / "feature_importance.png"))


def about_page():
    st.markdown('<div class="mq-eyebrow">About</div>', unsafe_allow_html=True)
    st.title("MatchIQ")
    st.write("AI football analytics for the Premier League, built by Ibrahim Bajwa "
             "(Computer Science, University of Calgary).")
    st.markdown("""
**How the predictor works**
1. 4,180 Premier League matches (2014-15 to 2024-25) from football-data.co.uk.
2. Every feature uses only games played *before* kickoff, so there's no peeking at the result.
3. Elo ratings track team strength; last-5 form adds points, goals, shots and shots on target.
4. Models are trained on older seasons and tested on the two newest (time-based split).
5. Logistic regression and XGBoost are compared to an always-home baseline and an Elo-only baseline.

**Coming next:** Player Scout ("find players like Saka") and Ask MatchIQ, a chatbot over both.

[Code on GitHub](https://github.com/ibrahimbajwaa/MatchIQ)
""")


pg = st.navigation([
    st.Page(predictor_page, title="Match Predictor", icon="⚽", default=True),
    st.Page(rankings_page, title="Power Rankings", icon="📈", url_path="rankings"),
    st.Page(performance_page, title="Model Performance", icon="🎯", url_path="performance"),
    st.Page(about_page, title="About", icon="ℹ️", url_path="about"),
])
pg.run()
