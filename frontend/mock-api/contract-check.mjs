// Checks that the JSON the mock API returns has exactly the fields and types of the Java DTO records in
// backend/src/main/java/dev/matchiq/api/Dtos.java. The frontend is built against the mock, so if this passes the
// frontend's expectations match what the Spring Boot service will send. Run:  npm run check:contract
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createApi, loadDataset } from "./api.mjs";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const source = readFileSync(join(repo, "backend/src/main/java/dev/matchiq/api/Dtos.java"), "utf8");

/** Splits "int a, Map<String, Object> b" on top-level commas only. */
function splitComponents(text) {
  const parts = [];
  let depth = 0;
  let current = "";
  for (const ch of text) {
    if (ch === "<") depth++;
    if (ch === ">") depth--;
    if (ch === "," && depth === 0) {
      parts.push(current);
      current = "";
    } else current += ch;
  }
  if (current.trim()) parts.push(current);
  return parts.map((p) => {
    const tokens = p.trim().split(/\s+/);
    return { name: tokens.pop(), type: tokens.join(" ") };
  });
}

const records = new Map();
for (const m of source.matchAll(/public record (\w+)\(([\s\S]*?)\)\s*\{\s*\}/g)) {
  records.set(m[1], splitComponents(m[2].replace(/\s+/g, " ")));
}
if (records.size === 0) throw new Error("found no records in Dtos.java");

const reached = new Set();
const errors = [];
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_INSTANT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

function check(type, value, path) {
  const fail = (why) => errors.push(`${path}: expected ${type}, ${why}`);
  const list = /^List<(.+)>$/.exec(type);
  if (list) {
    if (!Array.isArray(value)) return fail(`got ${typeof value}`);
    value.slice(0, 40).forEach((v, i) => check(list[1], v, `${path}[${i}]`));
    return;
  }
  if (/^Map<String, ?Object>$/.test(type)) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) fail("got a non-object");
    return;
  }
  if (records.has(type)) {
    reached.add(type);
    if (value === null || typeof value !== "object" || Array.isArray(value)) return fail(`got ${JSON.stringify(value)?.slice(0, 40)}`);
    const want = records.get(type).map((c) => c.name);
    const got = Object.keys(value);
    for (const k of want) if (!got.includes(k)) errors.push(`${path}: missing field '${k}'`);
    for (const k of got) if (!want.includes(k)) errors.push(`${path}: unexpected field '${k}' (not in ${type})`);
    for (const c of records.get(type)) if (c.name in value) check(c.type, value[c.name], `${path}.${c.name}`);
    return;
  }
  switch (type) {
    case "int": case "long":
      if (!Number.isInteger(value)) fail(`got ${JSON.stringify(value)}`);
      return;
    case "double":
      if (typeof value !== "number") fail(`got ${JSON.stringify(value)}`);
      return;
    case "boolean":
      if (typeof value !== "boolean") fail(`got ${JSON.stringify(value)}`);
      return;
    case "Integer": case "Long":
      if (value !== null && !Number.isInteger(value)) fail(`got ${JSON.stringify(value)}`);
      return;
    case "String":
      if (value !== null && typeof value !== "string") fail(`got ${JSON.stringify(value)}`);
      return;
    case "LocalDate":
      if (typeof value !== "string" || !ISO_DATE.test(value)) fail(`got ${JSON.stringify(value)}`);
      return;
    case "OffsetDateTime":
      if (typeof value !== "string" || !ISO_INSTANT.test(value)) fail(`got ${JSON.stringify(value)}`);
      return;
    default:
      errors.push(`${path}: the checker does not know the Java type '${type}'`);
  }
}

const handle = createApi(loadDataset());
const get = (url) => {
  const r = handle(url);
  if (r.status !== 200) errors.push(`${url}: status ${r.status}`);
  return r.body;
};

const firstId = get("/api/players?q=a&limit=1")[0].id;
const calls = [
  ["/api/overview", "Overview"],
  ["/api/stats", "List<StatDef>"],
  ["/api/leaderboards/expected_goals?limit=5", "LeaderboardPage"],
  ["/api/leaderboards/tackles?scope=defender&offset=10&limit=5", "LeaderboardPage"],
  ["/api/players?q=sa", "List<PlayerSummary>"],
  [`/api/players/${firstId}`, "PlayerProfile"],
  [`/api/players/${firstId}/similar?limit=5`, "List<SimilarPlayer>"],
  ["/api/scout/map", "ScoutMap"],
  ["/api/teams", "List<Team>"],
  ["/api/teams/ratings", "List<TeamRating>"],
  ["/api/fixtures?gameweek=2", "List<FixtureView>"],
  ["/api/fixtures?status=finished", "List<FixtureView>"],
  ["/api/predict?homeId=1&awayId=2", "Prediction"],
  ["/api/model", "ModelReport"],
];
for (const [url, type] of calls) check(type, get(url), url);

// Error responses are RFC 7807 problem details.
for (const url of ["/api/players/999999", "/api/leaderboards/goals_scored?scope=striker", "/api/predict?homeId=1&awayId=1"]) {
  const r = handle(url);
  if (![400, 404].includes(r.status)) errors.push(`${url}: expected 400 or 404, got ${r.status}`);
  for (const k of ["title", "status", "detail"]) if (!(k in r.body)) errors.push(`${url}: problem response lacks '${k}'`);
}

const unreached = [...records.keys()].filter((r) => !reached.has(r));
for (const r of unreached) errors.push(`DTO ${r} is never exercised by a checked route`);

if (errors.length) {
  console.error(`Contract check FAILED (${errors.length}):\n  ` + errors.slice(0, 30).join("\n  "));
  process.exit(1);
}
console.log(`Contract check passed: ${calls.length} routes match ${records.size} Java records (${[...records.keys()].join(", ")}).`);
