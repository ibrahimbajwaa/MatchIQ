"""MatchIQ web app.  Run locally with:  streamlit run app.py"""
import json
import sys
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from data import load_matches, download  # noqa: E402
from predict import (load_model, predict_fixture, recent_results,  # noqa: E402
                     current_teams, elo_table)

st.set_page_config(page_title="MatchIQ", page_icon=str(ROOT / "assets" / "favicon.png"),
                   layout="centered")

# Design tokens. Concept: a matchday scoreboard. One navy scoreboard panel is
# the hero; everything around it stays quiet on a cool chalk ground.
CHALK, LINE, INK, MUTED = "#f2f4f1", "#d8ddd6", "#13233a", "#5b6772"
HOME, DRAW, AWAY, LOSS = "#1e6b47", "#9aa39c", "#2f5f9e", "#b8473a"
DISPLAY = "'Barlow Condensed', 'Arial Narrow', sans-serif"
BODY = "'Barlow', 'Helvetica Neue', Arial, sans-serif"

CSS = f"""
@font-face {{ font-family: 'Barlow'; font-weight: 400; font-style: normal; font-display: swap; src: url('app/static/fonts/barlow-latin-400-normal.woff2') format('woff2'); }}
@font-face {{ font-family: 'Barlow'; font-weight: 500; font-style: normal; font-display: swap; src: url('app/static/fonts/barlow-latin-500-normal.woff2') format('woff2'); }}
@font-face {{ font-family: 'Barlow'; font-weight: 600; font-style: normal; font-display: swap; src: url('app/static/fonts/barlow-latin-600-normal.woff2') format('woff2'); }}
@font-face {{ font-family: 'Barlow Condensed'; font-weight: 500; font-style: normal; font-display: swap; src: url('app/static/fonts/barlow-condensed-latin-500-normal.woff2') format('woff2'); }}
@font-face {{ font-family: 'Barlow Condensed'; font-weight: 600; font-style: normal; font-display: swap; src: url('app/static/fonts/barlow-condensed-latin-600-normal.woff2') format('woff2'); }}
@font-face {{ font-family: 'Barlow Condensed'; font-weight: 700; font-style: normal; font-display: swap; src: url('app/static/fonts/barlow-condensed-latin-700-normal.woff2') format('woff2'); }}
html, body, .stMarkdown, .stMarkdown p, .stMarkdown li, [data-testid="stWidgetLabel"] p,
[data-baseweb="select"] div, .stDataFrame, input, textarea {{
  font-family: {BODY};
}}
.block-container {{ padding-top: 3.2rem; padding-bottom: 4rem; max-width: 860px; }}
h1, h2, h3 {{ font-family: {DISPLAY} !important; color: {INK}; letter-spacing: 0; }}
h1 {{ font-weight: 700 !important; font-size: 2.9rem !important; line-height: 1.02 !important; }}
h2 {{ font-weight: 600 !important; font-size: 1.75rem !important; }}
h3 {{ font-weight: 600 !important; font-size: 1.3rem !important; }}
p, li {{ font-size: 1.02rem; line-height: 1.6; color: {INK}; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ color: {MUTED} !important; font-size: .95rem; opacity: 1 !important; }}
[data-testid="stHeader"] a, [data-testid="stHeader"] button {{ font-family: {DISPLAY}; }}
[data-testid="stHeader"] [data-testid="stTopNavLink"] span,
[data-testid="stHeader"] nav a span {{ font-family: {DISPLAY}; font-size: 1.08rem; font-weight: 600; }}
.mq-wordmark {{ font-family: {DISPLAY}; font-weight: 700; font-size: 1.15rem; color: {INK};
  display: flex; align-items: center; gap: .5rem; margin-bottom: 1.6rem; }}
.mq-wordmark svg {{ flex: none; }}
.mq-wordmark span.sub {{ font-weight: 500; color: {MUTED}; }}

/* Scoreboard: the one bold element */
.mq-board {{ background: {INK}; color: #fff; border-radius: 12px; padding: 1.6rem 1.6rem 1.3rem;
  margin: .6rem 0 2.2rem; }}
.mq-fixture {{ display: grid; grid-template-columns: 1fr auto 1fr; align-items: end; gap: 1rem; }}
.mq-team {{ font-family: {DISPLAY}; font-weight: 700; font-size: clamp(1.9rem, 6vw, 3.1rem);
  line-height: 1; min-width: 0; overflow-wrap: anywhere; }}
.mq-team.away {{ text-align: right; }}
.mq-vs {{ font-family: {DISPLAY}; font-weight: 500; font-size: 1.2rem; color: #8ea0b8; padding-bottom: .35rem; }}
.mq-odds {{ display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 1.4rem; }}
.mq-odd .n {{ font-family: {DISPLAY}; font-weight: 600; font-size: clamp(2rem, 6.5vw, 3rem);
  line-height: 1; font-variant-numeric: tabular-nums; }}
.mq-odd .l {{ font-size: .92rem; color: #b9c5d4; margin-top: .25rem; }}
.mq-odd.draw {{ text-align: center; }} .mq-odd.away {{ text-align: right; }}
.mq-strip {{ display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 1.1rem; gap: 2px; }}
.mq-strip div {{ min-width: 2px; }}
.mq-board .fine {{ font-size: .85rem; color: #8ea0b8; margin-top: .9rem; }}

/* Form */
.mq-form {{ display: flex; flex-direction: column; gap: .35rem; margin-top: .4rem; }}
.mq-game {{ display: grid; grid-template-columns: 26px 1fr auto; gap: .6rem; align-items: center;
  font-size: .95rem; color: {INK}; }}
.mq-game .r {{ width: 26px; height: 26px; border-radius: 5px; display: grid; place-items: center;
  font-family: {DISPLAY}; font-weight: 700; color: #fff; font-size: .95rem; }}
.mq-game .score {{ font-variant-numeric: tabular-nums; font-weight: 600; }}
.mq-game .venue {{ color: {MUTED}; }}
.r.W {{ background: {HOME}; }} .r.D {{ background: {DRAW}; }} .r.L {{ background: {LOSS}; }}
.mq-colhead {{ font-family: {DISPLAY}; font-weight: 600; font-size: 1.25rem; color: {INK}; }}

/* Head-to-head stat rows */
.mq-h2h {{ display: flex; flex-direction: column; gap: .9rem; margin: .6rem 0 1.4rem; }}
.mq-row {{ display: grid; grid-template-columns: 3rem 1fr auto 1fr 3rem; align-items: center; gap: .6rem; }}
.mq-row .v {{ font-variant-numeric: tabular-nums; font-weight: 600; color: {INK}; }}
.mq-row .v.a {{ text-align: right; }}
.mq-row .lab {{ font-size: .9rem; color: {MUTED}; text-align: center; min-width: 7.5rem; }}
.mq-row .track {{ height: 8px; background: {LINE}; border-radius: 4px; display: flex; }}
.mq-row .track.h {{ justify-content: flex-end; }}
.mq-row .fill {{ height: 100%; border-radius: 4px; }}
.mq-keyline {{ border-top: 1px solid {LINE}; margin: 2.2rem 0 1.4rem; }}

/* Stat line on performance page */
.mq-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1rem 0 1.6rem;
  border-top: 2px solid {INK}; padding-top: .9rem; }}
.mq-stats .n {{ font-family: {DISPLAY}; font-weight: 600; font-size: 2.4rem; line-height: 1;
  color: {INK}; font-variant-numeric: tabular-nums; }}
.mq-stats .l {{ font-size: .9rem; color: {MUTED}; margin-top: .3rem; }}

@media (max-width: 640px) {{
  .mq-row {{ grid-template-columns: 2.4rem 1fr 2.4rem; }}
  .mq-row .lab {{ grid-column: 1 / -1; grid-row: 1; text-align: left; }}
  .mq-row .track {{ display: none; }}
  .mq-stats {{ grid-template-columns: 1fr; }}
}}
"""
# Streamlit's markdown ends an HTML block at a blank line, so strip them.
st.markdown("<style>" + "\n".join(l for l in CSS.splitlines() if l.strip()) + "</style>",
            unsafe_allow_html=True)


@alt.theme.register("matchiq", enable=True)
def chart_theme():
    return alt.theme.ThemeConfig({"config": {
        "font": "Barlow",
        "background": "transparent",
        "view": {"stroke": None},
        "axis": {"labelColor": MUTED, "titleColor": MUTED, "labelFontSize": 12,
                 "titleFontSize": 12, "titleFontWeight": 500, "gridColor": LINE,
                 "domainColor": LINE, "tickColor": LINE},
        "legend": {"labelColor": INK, "labelFontSize": 12, "titleColor": MUTED},
    }})


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
    r["f"] = r.pop("features").to_dict()
    return r


@st.cache_data
def get_metrics():
    return json.loads((ROOT / "reports" / "metrics.json").read_text())


@st.cache_data
def get_predictions():
    return pd.read_csv(ROOT / "reports" / "test_predictions.csv")


matches = get_matches()
TEAMS = current_teams(matches)
LAST_SEASON = matches.season.iloc[-1]

BALL = (f'<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">'
        f'<circle cx="12" cy="12" r="10.5" fill="none" stroke="{INK}" stroke-width="2"/>'
        f'<path d="M12 7.2l4.2 3-1.6 4.9H9.4L7.8 10.2z" fill="{HOME}"/></svg>')


def wordmark():
    st.markdown(f'<div class="mq-wordmark">{BALL}MatchIQ'
                f'<span class="sub">Premier League analytics</span></div>',
                unsafe_allow_html=True)


def html(s):
    """Render raw HTML. Lines are de-indented and blank lines dropped, because
    Streamlit's markdown treats indented lines as code and blank lines as breaks."""
    st.markdown("\n".join(l.strip() for l in s.splitlines() if l.strip()), unsafe_allow_html=True)


# ---------- pages ----------
def predictor_page():
    wordmark()
    st.title("Who wins?")
    st.caption(f"Pick any fixture. Predictions use Elo ratings and recent form "
               f"up to the end of the {LAST_SEASON} season.")

    c1, c2 = st.columns(2)
    home = c1.selectbox("Home team", TEAMS, index=TEAMS.index("Arsenal") if "Arsenal" in TEAMS else 0,
                        key="home")
    away_opts = [t for t in TEAMS if t != home]
    default_away = "Chelsea" if "Chelsea" in away_opts else away_opts[0]
    away = c2.selectbox("Away team", away_opts, index=away_opts.index(default_away), key="away")

    r = get_prediction(home, away)
    ph, pd_, pa = r["p_home"], r["p_draw"], r["p_away"]
    f = r["f"]
    H, A = escape(home), escape(away)

    html(f"""
<div class="mq-board" role="group" aria-label="Prediction for {H} versus {A}">
  <div class="mq-fixture">
    <div class="mq-team">{H}</div><div class="mq-vs">v</div><div class="mq-team away">{A}</div>
  </div>
  <div class="mq-odds">
    <div class="mq-odd"><div class="n">{ph:.0%}</div><div class="l">{H} win</div></div>
    <div class="mq-odd draw"><div class="n">{pd_:.0%}</div><div class="l">Draw</div></div>
    <div class="mq-odd away"><div class="n">{pa:.0%}</div><div class="l">{A} win</div></div>
  </div>
  <div class="mq-strip" aria-hidden="true">
    <div style="flex:{ph:.4f};background:{HOME}"></div>
    <div style="flex:{pd_:.4f};background:{DRAW}"></div>
    <div style="flex:{pa:.4f};background:#5b8fd6"></div>
  </div>
  <div class="fine">Elo {f['home_elo']:.0f} v {f['away_elo']:.0f}, home side gets a 60-point boost</div>
</div>""")

    st.subheader("Why the model thinks this")
    gap = f["home_elo"] - f["away_elo"]
    stronger = home if gap > 0 else away
    st.write(f"{stronger} is rated {abs(gap):.0f} Elo points higher. Elo is the model's strongest "
             f"signal: it rises after wins, especially against good teams, and falls after losses. "
             f"Playing at home adds a little more for {home}.")

    left, right = st.columns(2, gap="large")
    for col, team in ((left, home), (right, away)):
        games = recent_results(team, matches)
        rows = "".join(
            f'<div class="mq-game"><span class="r {g["result"]}" title="{g["result"]}">{g["result"]}</span>'
            f'<span>{escape(g["opponent"])} <span class="venue">({"home" if g["venue"] == "H" else "away"})</span></span>'
            f'<span class="score">{g["score"]}</span></div>'
            for g in reversed(games))
        with col:
            html(f'<div class="mq-colhead">{escape(team)}, last five</div>'
                 f'<div class="mq-form">{rows}</div>')

    html('<div class="mq-keyline"></div>')
    st.subheader("Recent form, head to head")
    st.caption("Averages over each team's last five league games.")
    stats = [("Points per game", "pts"), ("Goals scored", "gf"), ("Goals conceded", "ga"),
             ("Shots", "shots"), ("Shots on target", "sot")]
    rows = []
    for label, k in stats:
        hv, av = f[f"home_form_{k}"], f[f"away_form_{k}"]
        top = max(hv, av, 1e-9)
        rows.append(
            f'<div class="mq-row"><span class="v">{hv:.1f}</span>'
            f'<div class="track h"><div class="fill" style="width:{hv / top * 100:.0f}%;background:{HOME}"></div></div>'
            f'<span class="lab">{label}</span>'
            f'<div class="track"><div class="fill" style="width:{av / top * 100:.0f}%;background:{AWAY}"></div></div>'
            f'<span class="v a">{av:.1f}</span></div>')
    html(f'<div class="mq-h2h" aria-label="Form comparison">'
         f'<div class="mq-row"><span class="mq-colhead" style="grid-column:1/3">{H}</span>'
         f'<span></span><span class="mq-colhead" style="grid-column:4/6;text-align:right">{A}</span></div>'
         + "".join(rows) + "</div>")
    st.caption(f"Model: {r['model'].lower()}. It rarely names a draw as the single most likely "
               "result, but the draw percentage is still a meaningful estimate.")


def rankings_page():
    wordmark()
    st.title("Power rankings")
    st.caption(f"Elo rating for every team at the end of {LAST_SEASON}. An average Premier League "
               "side sits around 1500.")
    table = pd.DataFrame(elo_table(matches), columns=["Team", "Elo"])
    table["Elo"] = table["Elo"].round(0).astype(int)
    table["Rank"] = range(1, len(table) + 1)
    table["base"] = 1500
    table["side"] = (table.Elo >= 1500).map({True: "Above average", False: "Below average"})
    bars = alt.Chart(table).mark_bar(height=15, cornerRadius=2).encode(
        x=alt.X("Elo:Q", scale=alt.Scale(domain=[1200, 1800]),
                axis=alt.Axis(values=list(range(1200, 1801, 100)), format="d"),
                title="Elo rating"),
        x2="base:Q",
        y=alt.Y("Team:N", sort=alt.EncodingSortField("Elo", order="descending"), title=None,
                axis=alt.Axis(labelLimit=180, labelFontSize=13, labelColor=INK, ticks=False, domain=False)),
        color=alt.Color("side:N", scale=alt.Scale(domain=["Above average", "Below average"],
                                                   range=[HOME, LOSS]),
                        legend=alt.Legend(title=None, orient="top", symbolType="square")),
        tooltip=[alt.Tooltip("Rank:Q"), alt.Tooltip("Team:N"), alt.Tooltip("Elo:Q")])
    rule = alt.Chart(pd.DataFrame({"x": [1500]})).mark_rule(color=INK, strokeWidth=1).encode(x="x:Q")
    st.altair_chart((bars + rule).properties(height=600), width="stretch")
    st.dataframe(table[["Rank", "Team", "Elo"]], hide_index=True, width="stretch")


def performance_page():
    m = get_metrics()
    wordmark()
    st.title("How good is it?")
    st.write(f"The model learned from {m['train_matches']:,} matches (2015-16 to 2022-23), then "
             f"predicted all {m['test_matches']} matches of {' and '.join(m['test_seasons'])} "
             f"without seeing any of them first.")
    best = next(x for x in m["results"] if x["model"] == m["best_model"])
    home = next(x for x in m["results"] if x["model"] == "Always home win")
    html(f"""<div class="mq-stats">
  <div><div class="n">{best['accuracy']:.1%}</div><div class="l">MatchIQ picks the right result</div></div>
  <div><div class="n">{home['accuracy']:.1%}</div><div class="l">Always picking the home team</div></div>
  <div><div class="n">{m['test_matches']}</div><div class="l">Unseen test matches</div></div>
</div>""")

    st.subheader("Models against baselines")
    res = pd.DataFrame(m["results"])
    res["kind"] = res.model.isin(["Always home win", "Elo rating only"]).map(
        {True: "Baseline", False: "MatchIQ model"})
    res["pct"] = res.accuracy * 100
    base = alt.Chart(res).encode(
        y=alt.Y("model:N", sort=None, title=None,
                axis=alt.Axis(labelFontSize=13, labelColor=INK, ticks=False, domain=False, labelLimit=200)),
        x=alt.X("pct:Q", scale=alt.Scale(domain=[0, 65]), title="Accuracy on unseen matches (%)"))
    bars = base.mark_bar(height=22, cornerRadiusEnd=3).encode(
        color=alt.Color("kind:N", scale=alt.Scale(domain=["Baseline", "MatchIQ model"],
                                                  range=["#b9c0b9", HOME]),
                        legend=alt.Legend(title=None, orient="top", symbolType="square")),
        tooltip=[alt.Tooltip("model:N", title="Model"), alt.Tooltip("pct:Q", title="Accuracy %", format=".1f"),
                 alt.Tooltip("log_loss:Q", title="Log loss", format=".3f")])
    labels = base.mark_text(align="left", dx=6, fontSize=13, color=INK, fontWeight=600).encode(
        text=alt.Text("pct:Q", format=".1f"))
    st.altair_chart((bars + labels).properties(height=250), width="stretch")
    st.write("Elo ratings alone get almost the same accuracy as the full model. Adding recent form "
             "barely helps, which matches what published football models find.")

    st.subheader("Can you trust the percentages?")
    st.write("Each dot groups games by the home-win chance the model gave. If the model says 60%, "
             "home teams in that group should win about 60% of the time, so dots near the line "
             "mean honest probabilities.")
    p = get_predictions()
    p["bucket"] = pd.cut(p.p_home, [i / 10 for i in range(11)], include_lowest=True)
    cal = p.groupby("bucket", observed=True).agg(
        predicted=("p_home", "mean"), actual=("result", lambda s: (s == "H").mean()),
        games=("result", "size")).query("games >= 15").reset_index(drop=True)
    diag = alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(
        color="#b9c0b9", strokeDash=[5, 4]).encode(x="x:Q", y="y:Q")
    line = alt.Chart(cal).mark_line(color=HOME, strokeWidth=2.5, point=alt.OverlayMarkDef(
        size=90, filled=True, color=HOME, stroke=CHALK, strokeWidth=2)).encode(
        x=alt.X("predicted:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"),
                title="Home-win chance the model gave"),
        y=alt.Y("actual:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"),
                title="How often the home team won"),
        tooltip=[alt.Tooltip("predicted:Q", title="Model said", format=".0%"),
                 alt.Tooltip("actual:Q", title="Actually won", format=".0%"),
                 alt.Tooltip("games:Q", title="Games")])
    st.altair_chart((diag + line).properties(height=380), width="stretch")

    st.subheader("Season by season")
    seasons = pd.DataFrame(m["per_season"]).rename(columns={
        "season": "Season", "matches": "Matches", "model_accuracy": "MatchIQ",
        "home_accuracy": "Home team won"})
    st.dataframe(seasons.style.format({"MatchIQ": "{:.1%}", "Home team won": "{:.1%}"}),
                 hide_index=True, width="stretch")
    st.caption("Home advantage was unusually weak in 2024-25, which made that season harder to call.")


def about_page():
    wordmark()
    st.title("About MatchIQ")
    st.write("MatchIQ is a Premier League analytics project by Ibrahim Bajwa, a Computer Science "
             "student at the University of Calgary.")
    st.subheader("How the predictor works")
    st.markdown("""
1. **Data.** 4,180 Premier League matches from 2014-15 to 2024-25, from football-data.co.uk.
2. **No peeking.** Every feature for a match uses only games played before kickoff.
3. **Team strength.** Elo ratings rise after wins and fall after losses, with bigger wins counting more.
4. **Recent form.** Points, goals, shots and shots on target over each team's last five games.
5. **Honest testing.** Train on older seasons, test on the two newest ones the model never saw.
""")
    st.subheader("Coming next")
    st.write("Player Scout, for finding players with similar playing styles, and Ask MatchIQ, "
             "a chatbot that answers questions using the predictor and the scout.")
    st.markdown("[View the code on GitHub](https://github.com/ibrahimbajwaa/MatchIQ)")


pg = st.navigation([
    st.Page(predictor_page, title="Predictor", default=True),
    st.Page(rankings_page, title="Power rankings", url_path="rankings"),
    st.Page(performance_page, title="Model performance", url_path="performance"),
    st.Page(about_page, title="About", url_path="about"),
], position="top")
pg.run()
