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

from data import (load_matches, download, download_current,  # noqa: E402
                  load_current_season, CURRENT_SEASON)
from predict import (load_model, predict_fixture, recent_results,  # noqa: E402
                     current_teams, elo_table)
from scout import Scout, load_players, download as download_players, FEATURES as SCOUT_FEATURES, \
    LABELS as SCOUT_LABELS, SEASON as SCOUT_SEASON, MIN_MINUTES  # noqa: E402

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

/* Fixture list */
.mq-fxlist {{ display: flex; flex-direction: column; }}
.mq-fx {{ display: grid; grid-template-columns: 6.5rem 1fr 9.5rem; grid-template-rows: auto auto;
  column-gap: 1rem; row-gap: .45rem; align-items: center; padding: .8rem 0; border-top: 1px solid {LINE}; }}
.mq-fx .when {{ color: {MUTED}; font-size: .9rem; }}
.mq-fx .teams {{ font-family: {DISPLAY}; font-weight: 500; font-size: 1.2rem; color: {MUTED}; min-width: 0; }}
.mq-fx .teams .pick {{ color: {INK}; font-weight: 700; }}
.mq-fx .teams .v {{ color: {MUTED}; font-size: 1rem; padding: 0 .2rem; }}
.mq-fx .nums, .mq-fxhead .nums {{ display: grid; grid-template-columns: repeat(3, 1fr); text-align: right;
  font-variant-numeric: tabular-nums; font-weight: 600; color: {INK}; }}
.mq-fxhead {{ display: grid; grid-template-columns: 6.5rem 1fr 9.5rem; column-gap: 1rem; }}
.mq-fxhead .nums {{ font-weight: 500; color: {MUTED}; font-size: .85rem; padding-bottom: .3rem; }}
.mq-strip.mini {{ grid-column: 2 / 4; height: 5px; margin-top: 0; }}
/* Scout */
.mq-card {{ display: grid; grid-template-columns: 1fr auto; gap: .2rem 1rem; padding: 1.2rem 0 1rem;
  border-top: 2px solid {INK}; border-bottom: 1px solid {LINE}; margin: .4rem 0 1.4rem; }}
.mq-card .nm {{ font-family: {DISPLAY}; font-weight: 700; font-size: 2.3rem; line-height: 1; color: {INK}; }}
.mq-card .meta {{ color: {MUTED}; font-size: .98rem; }}
.mq-card .style {{ grid-row: 1 / 3; grid-column: 2; align-self: center; font-family: {DISPLAY};
  font-weight: 600; font-size: 1.15rem; color: #fff; padding: .35rem .8rem; border-radius: 6px; }}
.mq-pct {{ display: flex; flex-direction: column; gap: .55rem; margin: .4rem 0 .6rem; }}
.mq-pct .row {{ display: grid; grid-template-columns: 11rem 1fr 2rem 2.8rem; gap: .7rem; align-items: center; }}
.mq-pct .lab {{ font-size: .92rem; color: {INK}; line-height: 1.25; }}
.mq-pct .track {{ height: 10px; background: {LINE}; border-radius: 5px; overflow: hidden; }}
.mq-pct .fill {{ height: 100%; border-radius: 5px; }}
.mq-pct .p {{ font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; color: {INK}; }}
.mq-pct .raw {{ font-size: .85rem; color: {MUTED}; font-variant-numeric: tabular-nums; text-align: right; }}
.mq-sim {{ display: flex; flex-direction: column; }}
.mq-sim .row {{ display: grid; grid-template-columns: 1.4rem 1fr 4.5rem 2.8rem; gap: .8rem; align-items: center;
  padding: .55rem 0; border-top: 1px solid {LINE}; }}
.mq-sim .rk {{ color: {MUTED}; font-variant-numeric: tabular-nums; }}
.mq-sim .who {{ min-width: 0; }}
.mq-sim .who b {{ font-family: {DISPLAY}; font-weight: 600; font-size: 1.15rem; color: {INK}; }}
.mq-sim .who span {{ color: {MUTED}; font-size: .9rem; }}
.mq-sim .bar {{ height: 6px; background: {LINE}; border-radius: 3px; overflow: hidden; }}
.mq-sim .bar div {{ height: 100%; background: {HOME}; }}
.mq-sim .s {{ text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; color: {INK}; }}
@media (max-width: 640px) {{
  .mq-row {{ grid-template-columns: 2.4rem 1fr 2.4rem; }}
  .mq-row .lab {{ grid-column: 1 / -1; grid-row: 1; text-align: left; }}
  .mq-row .track {{ display: none; }}
  .mq-stats {{ grid-template-columns: 1fr; }}
  .mq-fx, .mq-fxhead {{ grid-template-columns: 1fr 8.5rem; }}
  .mq-fx .when {{ grid-column: 1 / -1; }}
  .mq-fxhead span:first-child {{ display: none; }}
  .mq-strip.mini {{ grid-column: 1 / -1; }}
  .mq-pct .row {{ grid-template-columns: 1fr 2.6rem; }}
  .mq-pct .track, .mq-pct .raw {{ display: none; }}
  .mq-sim .row {{ grid-template-columns: 1.4rem 1fr 3rem; }}
  .mq-sim .bar {{ display: none; }}
  .mq-card .nm {{ font-size: 1.9rem; }}
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
@st.cache_data(ttl=3 * 3600, show_spinner="Loading every Premier League match since 2014…")
def get_data():
    """All finished matches plus this season's remaining fixtures. Refreshed
    every 3 hours so new results appear without redeploying."""
    download()  # completed seasons: no-op when the CSVs are already saved
    try:
        source = download_current()
    except RuntimeError:
        source = "Saved copy"
    matches = load_matches()
    _, upcoming = load_current_season()
    return matches, upcoming, source


@st.cache_resource
def get_model():
    return load_model()


@st.cache_data(show_spinner=False)
def get_prediction(home, away, stamp):
    """`stamp` (latest result date) makes the cache refresh when new results arrive."""
    r = predict_fixture(home, away, matches, get_model())
    r["f"] = r.pop("features").to_dict()
    return r


@st.cache_data
def get_metrics():
    return json.loads((ROOT / "reports" / "metrics.json").read_text())


@st.cache_data
def get_predictions():
    return pd.read_csv(ROOT / "reports" / "test_predictions.csv")


@st.cache_resource(show_spinner="Building the player scout…")
def get_scout():
    download_players()
    return Scout(load_players())


matches, upcoming, DATA_SOURCE = get_data()
TEAMS = current_teams()
LAST_RESULT = matches.Date.max()
STAMP = f"{LAST_RESULT:%Y-%m-%d %H:%M}"
FRESHNESS = f"results up to {LAST_RESULT:%-d %B %Y}"

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
    st.caption(f"Pick any {CURRENT_SEASON} fixture. Predictions use every Premier League result "
               f"since 2014, {FRESHNESS}.")

    c1, c2 = st.columns(2)
    home = c1.selectbox("Home team", TEAMS, index=TEAMS.index("Arsenal") if "Arsenal" in TEAMS else 0,
                        key="home")
    away_opts = [t for t in TEAMS if t != home]
    default_away = "Chelsea" if "Chelsea" in away_opts else away_opts[0]
    away = c2.selectbox("Away team", away_opts, index=away_opts.index(default_away), key="away")

    r = get_prediction(home, away, STAMP)
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
    st.write(f"{stronger} is rated {abs(gap):.0f} Elo points higher. The model works from Elo ratings: "
             f"a team's rating rises after wins, especially against good teams, and falls after "
             f"losses. Playing at home adds a little more for {home}.")

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
    st.caption("Form is shown for context. The model itself uses Elo ratings only, because adding "
               "form didn't improve predictions on unseen seasons (see Model performance). It rarely "
               "names a draw as the single most likely result, but the draw percentage is still a "
               "meaningful estimate.")

    html('<div class="mq-keyline"></div>')
    next_fixtures()


def next_fixtures():
    todo = upcoming[upcoming.Date > LAST_RESULT]
    if todo.empty:
        return
    gw = int(todo.gameweek.iloc[0])
    games = todo[todo.gameweek == gw]
    st.subheader(f"Gameweek {gw} predictions")
    note = ""
    if games.Date.min() < pd.Timestamp.now():
        note = (" The data feed hasn't recorded these results yet, so some of these games may "
                "already have been played.")
    st.caption(f"Every fixture in the next gameweek, predicted with {FRESHNESS}.{note}")
    rows = []
    for g in games.itertuples():
        r = get_prediction(g.HomeTeam, g.AwayTeam, STAMP)
        ph, pd_, pa = r["p_home"], r["p_draw"], r["p_away"]
        pick = g.HomeTeam if ph >= max(pd_, pa) else g.AwayTeam if pa >= pd_ else "Draw"
        rows.append(
            f'<div class="mq-fx"><div class="when">{g.Date:%a %-d %b}</div>'
            f'<div class="teams"><span class="{"pick" if pick == g.HomeTeam else ""}">{escape(g.HomeTeam)}</span>'
            f' <span class="v">v</span> '
            f'<span class="{"pick" if pick == g.AwayTeam else ""}">{escape(g.AwayTeam)}</span></div>'
            f'<div class="nums"><span>{ph:.0%}</span><span>{pd_:.0%}</span><span>{pa:.0%}</span></div>'
            f'<div class="mq-strip mini"><div style="flex:{ph:.4f};background:{HOME}"></div>'
            f'<div style="flex:{pd_:.4f};background:{DRAW}"></div>'
            f'<div style="flex:{pa:.4f};background:{AWAY}"></div></div></div>')
    html('<div class="mq-fxhead"><span></span><span></span><span class="nums"><span>Home</span>'
         '<span>Draw</span><span>Away</span></span></div>'
         f'<div class="mq-fxlist">{"".join(rows)}</div>')


def rankings_page():
    wordmark()
    st.title("Power rankings")
    st.caption(f"Elo rating for every {CURRENT_SEASON} team, {FRESHNESS}. An average Premier League "
               "side sits around 1500, and newly promoted sides start at 1420.")
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
    st.write(f"The model learned from {m['train_matches']:,} matches ({m['train_seasons'][0]} to "
             f"{m['train_seasons'][1]}), then "
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
    st.write(f"I chose the model on a separate season ({m['validation_season']}) before looking at the "
             f"test seasons. Elo ratings alone did as well as models with recent form added, so the "
             f"app uses Elo only. That matches what published football models find: a good "
             f"team-strength rating is hard to beat with box-score stats.")

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
    st.caption("Home advantage was unusually weak in both test seasons (home teams won about 42% "
               "of games, against about 45% in earlier seasons), which makes them harder to call.")


STYLE_COLORS = {"Goal threats": LOSS, "Creators": AWAY, "Defensive stoppers": INK, "Ball-winners": HOME}


def scout_page():
    wordmark()
    sc = get_scout()
    P = sc.players
    names = sc.style_names()
    styles = pd.Series(sc.cluster).map(names)
    st.title("Player scout")
    st.caption(f"Find players who play alike, based on {SCOUT_SEASON} Premier League stats for every "
               f"outfield player with {MIN_MINUTES}+ minutes ({len(P)} players).")

    order = P.sort_values("name")
    labels = {i: f"{r['name']} ({r['team']})" for i, r in order.iterrows()}
    default = int(P.index[P.name == "Saka"][0]) if (P.name == "Saka").any() else int(order.index[0])
    c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
    i = c1.selectbox("Player", list(labels), index=list(labels).index(default),
                     format_func=labels.get, key="scout_player")
    same_pos = c2.toggle("Same position only", value=False, key="scout_samepos")
    me = P.loc[i]
    style = styles[i]

    html(f"""<div class="mq-card">
<div class="nm">{escape(me['name'])}</div>
<div class="style" style="background:{STYLE_COLORS.get(style, MUTED)}">{escape(style)}</div>
<div class="meta">{escape(me.full_name)}, {escape(me.team)}, {me.position.lower()}, {int(me.minutes):,} minutes</div>
</div>""")

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.subheader("Scouting report")
        st.caption(f"Percentile per 90 minutes against other {me.position.lower()}s. "
                   "90 means better than 90% of them.")
        pct = sc.percentiles(me["name"])
        rows = []
        for f in SCOUT_FEATURES:
            v = float(pct[f])
            col = HOME if v >= 80 else "#7fa892" if v >= 40 else "#b9c0b9"
            rows.append(f'<div class="row"><span class="lab">{escape(SCOUT_LABELS[f])}</span>'
                        f'<div class="track"><div class="fill" style="width:{v:.0f}%;background:{col}"></div></div>'
                        f'<span class="p">{v:.0f}</span><span class="raw">{me[f]:.2f}</span></div>')
        html('<div class="mq-pct">' + "".join(rows) + "</div>")
        st.caption("Right-hand numbers are the raw per-90 values. Threat and creativity are "
                   "Opta-based indexes from the official Fantasy Premier League data.")
    with right:
        st.subheader("Plays most like")
        sim = sc.similar(me["name"], n=10, same_position=same_pos)
        rows = []
        for rank, (_, r) in enumerate(sim.iterrows(), 1):
            pct_match = max(r.similarity, 0) * 100
            rows.append(f'<div class="row"><span class="rk">{rank}</span>'
                        f'<span class="who"><b>{escape(r["name"])}</b><br><span>{escape(r.team)}, '
                        f'{r.position.lower()}</span></span>'
                        f'<div class="bar"><div style="width:{pct_match:.0f}%"></div></div>'
                        f'<span class="s">{pct_match:.0f}%</span></div>')
        html('<div class="mq-sim">' + "".join(rows) + "</div>")
        st.caption("Match % is cosine similarity of the two players' standardised per-90 profiles: "
                   "it compares what a player does, not how famous they are.")

    html('<div class="mq-keyline"></div>')
    st.subheader("Style map")
    st.caption(f"Every player, squashed from {len(SCOUT_FEATURES)} stats into two dimensions. Players close "
               f"together play alike. Colours are the {sc.k} playing styles found by k-means clustering.")
    top = set(sim.index[:5])
    mp = P.assign(x=sc.xy[:, 0], y=sc.xy[:, 1], style=styles,
                  role=["Selected" if j == i else "Most similar" if j in top else "Other" for j in P.index])
    dom = [n for n in STYLE_COLORS if n in set(styles)] + sorted(set(styles) - set(STYLE_COLORS))
    rng = [STYLE_COLORS.get(n, MUTED) for n in dom]
    base = alt.Chart(mp).encode(
        x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None),
        tooltip=[alt.Tooltip("name:N", title="Player"), alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("position:N", title="Position"), alt.Tooltip("style:N", title="Style")])
    dots = base.transform_filter("datum.role == 'Other'").mark_point(filled=True, size=46, opacity=.55).encode(
        color=alt.Color("style:N", scale=alt.Scale(domain=dom, range=rng),
                        legend=alt.Legend(title=None, orient="top", symbolOpacity=1)),
        shape=alt.Shape("style:N", scale=alt.Scale(domain=dom), legend=None))
    near = base.transform_filter("datum.role == 'Most similar'").mark_point(
        filled=True, size=110, stroke="#fff", strokeWidth=1.5).encode(
        color=alt.Color("style:N", scale=alt.Scale(domain=dom, range=rng), legend=None),
        shape=alt.Shape("style:N", scale=alt.Scale(domain=dom), legend=None))
    sel = base.transform_filter("datum.role == 'Selected'").mark_point(
        size=420, filled=False, strokeWidth=3, color=INK, shape="circle")
    lab = base.transform_filter("datum.role != 'Other'").mark_text(
        dx=10, dy=-9, align="left", fontSize=13, fontWeight=600, color=INK).encode(text="name:N")
    st.altair_chart((dots + near + sel + lab).properties(height=460), width="stretch")
    with st.expander("How the playing styles were found"):
        st.write(f"I tried k-means with 4 to 8 groups and kept the number with the best silhouette "
                 f"score (k = {sc.k}, score {sc.silhouette[sc.k]:.2f}). A score that low means the "
                 "styles overlap, which is realistic: plenty of players sit between two roles. "
                 "Each group is named after the stat it stands out on most.")
        cent = sc.centroids().rename(index=names, columns=SCOUT_LABELS).T.round(2)
        st.dataframe(cent, width="stretch")
        st.caption("Average z-score per style: above 0 means more than a typical player.")


def about_page():
    wordmark()
    st.title("About MatchIQ")
    st.write("MatchIQ is a Premier League analytics project by Ibrahim Bajwa, a Computer Science "
             "student at the University of Calgary.")
    st.subheader("How the predictor works")
    st.markdown("""
1. **Data.** Every Premier League match since 2014-15 from football-data.co.uk, plus this season's results from the official Fantasy Premier League feed.
2. **No peeking.** Every feature for a match uses only games played before kickoff.
3. **Team strength.** Elo ratings rise after wins and fall after losses, with bigger wins counting more.
4. **Recent form.** Points, goals, shots and shots on target over each team's last five games.
5. **Honest testing.** Train on older seasons, test on the two newest ones the model never saw.
""")
    st.subheader("How the player scout works")
    st.markdown(f"""
1. **Data.** {SCOUT_SEASON} stats for every outfield player with {MIN_MINUTES}+ minutes, from the
   official Fantasy Premier League data (Opta-based).
2. **Per 90.** Counting stats become per-90-minute rates so part-time and full-time players compare fairly.
3. **Similarity.** Stats are standardised, then players are compared with cosine similarity.
4. **Styles.** K-means clustering groups players into playing styles.
""")
    st.subheader("Coming next")
    st.write("Ask MatchIQ, a chatbot that answers questions using the predictor and the scout.")
    st.markdown("[View the code on GitHub](https://github.com/ibrahimbajwaa/MatchIQ)")


pg = st.navigation([
    st.Page(predictor_page, title="Predictor", default=True),
    st.Page(scout_page, title="Player scout", url_path="scout"),
    st.Page(rankings_page, title="Power rankings", url_path="rankings"),
    st.Page(performance_page, title="Model performance", url_path="performance"),
    st.Page(about_page, title="About", url_path="about"),
], position="top")
pg.run()
