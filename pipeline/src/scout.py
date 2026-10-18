"""Player Scout: find players with similar statistical profiles.

Data: official Fantasy Premier League player stats for the 2025-26 season
(mirrored by vaastav/Fantasy-Premier-League), which include Opta-derived
expected goals (xG), expected assists (xA), creativity, threat and
defensive actions for every player.

Method
1. Keep outfield players with at least MIN_MINUTES so per-90 numbers are stable.
2. Convert counting stats to per-90-minute rates, so a player who played
   1,000 minutes is comparable with one who played 3,000.
3. Standardise each stat (z-scores) so no single stat dominates.
4. Similarity = cosine similarity between two players' stat vectors: it
   compares the *shape* of a profile (what a player does), not just volume.
5. Playing styles = k-means clustering on the same vectors; k is chosen with
   the silhouette score.
"""
from pathlib import Path
import urllib.request

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from data import FPL_TO_FD, FPL_URL

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SEASON = "2025-26"
MIN_MINUTES = 900
POSITIONS = {2: "Defender", 3: "Midfielder", 4: "Forward"}

# (column in the FPL data, label shown in the app)
STATS = [
    ("goals_scored", "Goals"),
    ("expected_goals", "Expected goals (xG)"),
    ("assists", "Assists"),
    ("expected_assists", "Expected assists (xA)"),
    ("threat", "Threat (shooting chances)"),
    ("creativity", "Creativity (chances made)"),
    ("tackles", "Tackles"),
    ("clearances_blocks_interceptions", "Clearances, blocks, interceptions"),
    ("recoveries", "Ball recoveries"),
]
FEATURES = [f"{c}_p90" for c, _ in STATS]
LABELS = {f"{c}_p90": label for c, label in STATS}


def download(force=False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for file in ("players_raw.csv", "teams.csv"):
        path = RAW_DIR / f"fpl-{SEASON}-{file}"
        if force or not path.exists():
            urllib.request.urlretrieve(FPL_URL.format(season=SEASON, file=file), path)


def load_players():
    """Outfield players with enough minutes, with per-90 stats."""
    p = pd.read_csv(RAW_DIR / f"fpl-{SEASON}-players_raw.csv")
    teams = pd.read_csv(RAW_DIR / f"fpl-{SEASON}-teams.csv")
    team_name = {r.id: FPL_TO_FD.get(r.name, r.name) for r in teams.itertuples()}
    p = p[(p.minutes >= MIN_MINUTES) & p.element_type.isin(POSITIONS)].copy()
    p["name"] = p.web_name
    # Two players with the same short name: add first initial
    dup = p.name.duplicated(keep=False)
    p.loc[dup, "name"] = p.loc[dup, "first_name"].str[0] + ". " + p.loc[dup, "web_name"]
    p["full_name"] = p.first_name + " " + p.second_name
    p["team"] = p.team.map(team_name)
    p["position"] = p.element_type.map(POSITIONS)
    for col, _ in STATS:
        p[f"{col}_p90"] = pd.to_numeric(p[col], errors="coerce").fillna(0) / p.minutes * 90
    cols = ["id", "name", "full_name", "team", "position", "minutes"] + [c for c, _ in STATS] + FEATURES
    return p[cols].reset_index(drop=True)


class Scout:
    def __init__(self, players: pd.DataFrame, seed: int = 42):
        self.players = players
        self.X = StandardScaler().fit_transform(players[FEATURES])
        norms = np.linalg.norm(self.X, axis=1, keepdims=True)
        self.unit = self.X / np.where(norms == 0, 1, norms)
        # Percentile of each stat within the player's own position
        self.pct = players.groupby("position")[FEATURES].rank(pct=True) * 100
        # Playing-style clusters: pick k by silhouette score
        scores = {}
        for k in range(4, 9):
            km = KMeans(n_clusters=k, n_init=20, random_state=seed).fit(self.X)
            scores[k] = silhouette_score(self.X, km.labels_)
        self.k = max(scores, key=scores.get)
        self.silhouette = scores
        self.kmeans = KMeans(n_clusters=self.k, n_init=20, random_state=seed).fit(self.X)
        self.cluster = self.kmeans.labels_
        # 2-D map of all players for plotting
        self.pca = PCA(n_components=2, random_state=seed).fit(self.X)
        self.xy = self.pca.transform(self.X)

    def index_of(self, name):
        hits = self.players.index[self.players.name == name]
        if len(hits) == 0:
            raise ValueError(f"No player called {name!r} with {MIN_MINUTES}+ minutes")
        return hits[0]

    def similar(self, name, n=10, same_position=False):
        i = self.index_of(name)
        sim = self.unit @ self.unit[i]
        out = self.players.assign(similarity=sim, style=self.cluster)
        out = out.drop(index=i)
        if same_position:
            out = out[out.position == self.players.position[i]]
        return out.sort_values("similarity", ascending=False).head(n)

    def percentiles(self, name):
        i = self.index_of(name)
        return self.pct.loc[i]

    def centroids(self):
        """Average z-score of every stat for each cluster (for naming styles)."""
        return pd.DataFrame(self.kmeans.cluster_centers_, columns=FEATURES)

    def style_names(self):
        """Name each cluster by the stat it stands out on most.

        Assigned greedily: the cluster highest on xG is the goal threats, then
        the highest remaining on xA are creators, and so on. Any extra clusters
        (if k > 4) get a generic name.
        """
        c = self.centroids()
        rules = [("expected_goals_p90", "Goal threats"),
                 ("expected_assists_p90", "Creators"),
                 ("clearances_blocks_interceptions_p90", "Defensive stoppers"),
                 ("recoveries_p90", "Ball-winners")]
        names, left = {}, set(range(self.k))
        for col, label in rules:
            if not left:
                break
            pick = max(left, key=lambda i: c.loc[i, col])
            names[pick] = label
            left.remove(pick)
        for i in sorted(left):
            names[i] = f"All-rounders {i + 1}"
        return names

    def style_of(self, name):
        return self.style_names()[self.cluster[self.index_of(name)]]


if __name__ == "__main__":
    download()
    players = load_players()
    s = Scout(players)
    print(f"{len(players)} outfield players with {MIN_MINUTES}+ minutes in {SEASON}")
    print("Silhouette by k:", {k: round(v, 3) for k, v in s.silhouette.items()}, "-> k =", s.k)
    print(s.centroids().round(2).rename(columns=LABELS).T.to_string())
    for c in range(s.k):
        members = players[s.cluster == c]
        print(f"\nCluster {c} ({len(members)}): positions {members.position.value_counts().to_dict()}")
        print("  ", ", ".join(members.sort_values("minutes", ascending=False).name.head(12)))
