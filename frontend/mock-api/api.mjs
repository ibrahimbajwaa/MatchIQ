// A dependency-free stand-in for the Spring Boot API. It answers every route with the same JSON shapes (see
// backend/src/main/java/dev/matchiq/api/Dtos.java and docs/api.md), computed from pipeline/out/dataset.json, so the
// frontend can be built and tested without Java, Postgres or Redis.
//
// It deliberately repeats the backend's rules: leaderboards order by score then player id (both descending), ranks are
// competition ranks, similarity is cosine similarity over z-scores, and predictions use the exported model file.
// `contract-check.mjs` verifies the field names and types against the Java DTOs, so the two cannot drift silently.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, "..", "..");

export function loadDataset() {
  const dataset = JSON.parse(readFileSync(join(repo, "pipeline/out/dataset.json"), "utf8"));
  const props = Object.fromEntries(
    readFileSync(join(repo, "backend/src/main/resources/model/elo_logit.properties"), "utf8")
      .split("\n")
      .filter((l) => l.trim() && !l.startsWith("#"))
      .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
  );
  const nums = (s) => s.split(",").map(Number);
  const model = {
    name: props.name,
    homeAdvantage: Number(props.homeAdvantage),
    mean: Number(props.mean),
    scale: Number(props.scale),
    coef: nums(props.coef), // order: away, draw, home
    intercept: nums(props.intercept),
  };
  return { dataset, model };
}

const SCOPES = { all: "all", defender: "Defender", midfielder: "Midfielder", forward: "Forward" };

class HttpError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
  }
}

export function createApi({ dataset: ds, model }) {
  const teams = [...ds.teams].sort((a, b) => Number(b.inLeague) - Number(a.inLeague) || b.elo - a.elo || a.id - b.id);
  const teamById = new Map(teams.map((t) => [t.id, t]));
  const statDefs = [...ds.statDefs].sort((a, b) => a.sortOrder - b.sortOrder);
  const statByKey = new Map(statDefs.map((s) => [s.key, s]));
  const playerById = new Map(ds.players.map((p) => [p.id, p]));

  const statsOf = new Map(); // player id -> stat key -> row
  for (const s of ds.playerStats) {
    if (!statsOf.has(s.playerId)) statsOf.set(s.playerId, new Map());
    statsOf.get(s.playerId).set(s.statKey, s);
  }

  const summary = (p) => {
    const t = teamById.get(p.teamId);
    return {
      id: p.id, name: p.name, fullName: p.fullName, teamId: p.teamId, teamName: t.displayName,
      teamShort: t.shortName, position: p.position, minutes: p.minutes, style: p.style,
    };
  };

  // ---- leaderboards
  const boards = new Map();
  const boardOf = (stat, scope) => {
    const key = `${stat}|${scope}`;
    if (!boards.has(key)) {
      const rows = ds.players
        .filter((p) => scope === "all" || p.position === scope)
        .map((p) => ({ id: p.id, score: statsOf.get(p.id).get(stat).per90 }))
        .sort((a, b) => b.score - a.score || b.id - a.id);
      boards.set(key, rows);
    }
    return boards.get(key);
  };
  const countGreater = (rows, score) => rows.filter((r) => r.score > score).length;

  // ---- similarity
  const vectors = ds.players.map((p) => {
    const z = statDefs.map((d) => statsOf.get(p.id).get(d.key).zscore);
    const norm = Math.hypot(...z);
    return { id: p.id, position: p.position, unit: z.map((v) => (norm === 0 ? 0 : v / norm)) };
  });
  const similar = (id, limit, samePosition) => {
    const q = vectors.find((v) => v.id === id);
    return vectors
      .filter((v) => v.id !== id && (!samePosition || v.position === q.position))
      .map((v) => ({ id: v.id, similarity: v.unit.reduce((s, x, i) => s + x * q.unit[i], 0) }))
      .sort((a, b) => b.similarity - a.similarity || a.id - b.id)
      .slice(0, limit);
  };

  // ---- predictions
  const predict = (homeElo, awayElo) => {
    const x = (homeElo + model.homeAdvantage - awayElo - model.mean) / model.scale;
    const s = model.coef.map((c, i) => c * x + model.intercept[i]);
    const m = Math.max(...s);
    const e = s.map((v) => Math.exp(v - m));
    const sum = e.reduce((a, b) => a + b, 0);
    return { pAway: e[0] / sum, pDraw: e[1] / sum, pHome: e[2] / sum };
  };
  const teamRef = (t) => ({ id: t.id, shortName: t.shortName, displayName: t.displayName });
  const iso = (kickoff) => kickoff.replace(" ", "T").replace("+00", "Z");

  const history = new Map();
  for (const p of [...ds.eloPoints].sort((a, b) => a.teamId - b.teamId || a.pointNo - b.pointNo)) {
    if (!history.has(p.teamId)) history.set(p.teamId, []);
    history.get(p.teamId).push({ date: p.matchDate, elo: p.elo });
  }

  const int = (value, name, { min, max, fallback }) => {
    if (value === null || value === undefined || value === "") return fallback;
    const n = Number(value);
    if (!Number.isInteger(n) || n < min || n > max) throw new HttpError(400, `${name} must be a whole number from ${min} to ${max}`);
    return n;
  };

  const routes = [
    [/^\/api\/overview$/, () => {
      const upcoming = ds.fixtures.filter((f) => f.status === "UPCOMING");
      const chosen = ds.modelMetrics.find((m) => m.chosen);
      const baseline = ds.modelMetrics.find((m) => m.model === "Always home win");
      return {
        meta: ds.meta,
        counts: { players: ds.players.length, teams: teams.filter((t) => t.inLeague).length, fixtures: ds.fixtures.length, upcoming: upcoming.length },
        nextGameweek: upcoming.length ? Math.min(...upcoming.map((f) => f.gameweek)) : null,
        headline: { chosenModel: chosen.model, modelAccuracy: chosen.accuracy, baselineAccuracy: baseline.accuracy, testMatches: ds.meta.testMatches },
      };
    }],
    [/^\/api\/stats$/, () => statDefs.map((d) => ({ key: d.key, label: d.label, description: d.description }))],
    [/^\/api\/leaderboards\/([^/]+)$/, (q, [stat]) => {
      const def = statByKey.get(stat);
      if (!def) throw new HttpError(404, `Unknown stat '${stat}'`);
      const scope = SCOPES[(q.get("scope") ?? "all").toLowerCase()];
      if (!scope) throw new HttpError(400, `Unknown scope '${q.get("scope")}'. Use all, Defender, Midfielder or Forward.`);
      const offset = int(q.get("offset"), "offset", { min: 0, max: 1e9, fallback: 0 });
      const limit = int(q.get("limit"), "limit", { min: 1, max: 100, fallback: 25 });
      const rows = boardOf(stat, scope);
      const slice = rows.slice(offset, offset + limit);
      let rank = 0;
      const entries = slice.map((r, i) => {
        if (i === 0) rank = 1 + countGreater(rows, r.score);
        else if (r.score !== slice[i - 1].score) rank = offset + i + 1;
        const row = statsOf.get(r.id).get(stat);
        return { rank, player: summary(playerById.get(r.id)), per90: row.per90, raw: row.raw };
      });
      return { statKey: stat, label: def.label, scope, total: rows.length, offset, limit, entries };
    }],
    [/^\/api\/players$/, (q) => {
      const text = (q.get("q") ?? "").trim().toLowerCase();
      const limit = int(q.get("limit"), "limit", { min: 1, max: 25, fallback: 8 });
      if (!text) return [];
      return ds.players
        .filter((p) => p.name.toLowerCase().includes(text) || p.fullName.toLowerCase().includes(text))
        .sort((a, b) => Number(b.name.toLowerCase().startsWith(text)) - Number(a.name.toLowerCase().startsWith(text)) || b.minutes - a.minutes || a.id - b.id)
        .slice(0, limit)
        .map(summary);
    }],
    [/^\/api\/players\/(-?\d+)$/, (_q, [id]) => {
      const p = playerById.get(Number(id));
      if (!p) throw new HttpError(404, `No player with id ${id}`);
      return {
        player: summary(p),
        stats: statDefs.map((d) => {
          const s = statsOf.get(p.id).get(d.key);
          const board = boardOf(d.key, p.position);
          return {
            key: d.key, label: d.label, description: d.description, raw: s.raw, per90: s.per90, percentile: s.percentile,
            positionRank: 1 + countGreater(board, s.per90), positionTotal: board.length,
          };
        }),
      };
    }],
    [/^\/api\/players\/(-?\d+)\/similar$/, (q, [id]) => {
      const p = playerById.get(Number(id));
      if (!p) throw new HttpError(404, `No player with id ${id}`);
      const limit = int(q.get("limit"), "limit", { min: 1, max: 50, fallback: 10 });
      return similar(p.id, limit, q.get("samePosition") === "true").map((n) => ({ player: summary(playerById.get(n.id)), similarity: n.similarity }));
    }],
    [/^\/api\/scout\/map$/, () => ({
      styles: [...new Set(ds.players.map((p) => p.style))].sort(),
      points: [...ds.players].sort((a, b) => a.id - b.id).map((p) => ({
        id: p.id, name: p.name, teamShort: teamById.get(p.teamId).shortName, position: p.position, style: p.style, x: p.pcaX, y: p.pcaY,
      })),
    })],
    [/^\/api\/teams$/, (q) => (q.get("league") === "false" ? teams : teams.filter((t) => t.inLeague))
      .map((t) => ({ id: t.id, name: t.name, displayName: t.displayName, shortName: t.shortName, elo: t.elo, eloRank: t.eloRank, inLeague: t.inLeague }))],
    [/^\/api\/teams\/ratings$/, () => teams.filter((t) => t.inLeague).map((t) => ({
      id: t.id, name: t.name, displayName: t.displayName, shortName: t.shortName, elo: t.elo, eloRank: t.eloRank, inLeague: t.inLeague,
      history: history.get(t.id) ?? [],
    }))],
    [/^\/api\/fixtures$/, (q) => {
      const status = q.get("status")?.toUpperCase() ?? null;
      if (status && !["UPCOMING", "FINISHED"].includes(status)) throw new HttpError(400, `Unknown status '${q.get("status")}'. Use UPCOMING or FINISHED.`);
      const gameweek = q.get("gameweek") === null ? null : Number(q.get("gameweek"));
      return ds.fixtures
        .filter((f) => (gameweek === null || f.gameweek === gameweek) && (!status || f.status === status))
        .sort((a, b) => a.kickoff.localeCompare(b.kickoff) || a.id - b.id)
        .map((f) => ({
          id: f.id, gameweek: f.gameweek, kickoff: iso(f.kickoff), status: f.status, homeGoals: f.homeGoals, awayGoals: f.awayGoals,
          home: teamRef(teamById.get(f.homeTeamId)), away: teamRef(teamById.get(f.awayTeamId)),
          pHome: f.pHome, pDraw: f.pDraw, pAway: f.pAway, predicted: f.predicted, result: f.result,
        }));
    }],
    [/^\/api\/predict$/, (q) => {
      const homeId = Number(q.get("homeId"));
      const awayId = Number(q.get("awayId"));
      if (homeId === awayId) throw new HttpError(400, "Pick two different teams");
      const home = teamById.get(homeId);
      const away = teamById.get(awayId);
      if (!home) throw new HttpError(404, `No team with id ${q.get("homeId")}`);
      if (!away) throw new HttpError(404, `No team with id ${q.get("awayId")}`);
      const p = predict(home.elo, away.elo);
      const predicted = p.pHome >= p.pDraw && p.pHome >= p.pAway ? "H" : p.pDraw >= p.pAway ? "D" : "A";
      const side = (t) => ({ id: t.id, shortName: t.shortName, displayName: t.displayName, elo: t.elo });
      return {
        home: side(home), away: side(away), pHome: p.pHome, pDraw: p.pDraw, pAway: p.pAway, predicted,
        homeAdvantage: model.homeAdvantage, eloDiff: home.elo + model.homeAdvantage - away.elo, model: model.name,
      };
    }],
    [/^\/api\/model$/, () => ({
      chosenModel: ds.modelMetrics.find((m) => m.chosen).model,
      metrics: ds.modelMetrics, seasons: ds.modelSeasons, meta: ds.meta,
    })],
  ];

  /** Returns { status, body } for a request path with query string, like `/api/overview`. */
  return function handle(target) {
    const url = new URL(target, "http://mock.local");
    try {
      for (const [pattern, run] of routes) {
        const match = pattern.exec(url.pathname);
        if (match) return { status: 200, body: run(url.searchParams, match.slice(1)) };
      }
      throw new HttpError(404, `No route for ${url.pathname}`);
    } catch (e) {
      if (!(e instanceof HttpError)) throw e;
      return { status: e.status, body: { type: "about:blank", title: e.status === 404 ? "Not Found" : "Bad Request", status: e.status, detail: e.message } };
    }
  };
}
