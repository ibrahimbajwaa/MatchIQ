import type {
  FixtureView, LeaderboardPage, ModelReport, Overview, PlayerProfile, PlayerSummary, Prediction, Problem,
  Scope, ScoutMap, SimilarPlayer, StatDef, Team, TeamRating,
} from "./types";

// Empty in development and in the Docker image (same origin, /api is proxied). Set VITE_API_BASE at build time when
// the frontend is hosted separately from the API, for example on Vercel.
const BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(readonly status: number, readonly title: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type Params = Record<string, string | number | boolean | undefined>;

async function get<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) query.set(k, String(v));
  const qs = query.toString();
  let response: Response;
  try {
    response = await fetch(`${BASE}/api${path}${qs ? `?${qs}` : ""}`, { signal, headers: { accept: "application/json" } });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, "Can't reach the API", "The MatchIQ service isn't responding. Check that the backend is running and try again.");
  }
  if (!response.ok) {
    const problem = (await response.json().catch(() => ({}))) as Problem;
    throw new ApiError(response.status, problem.title ?? "Request failed", problem.detail ?? `The API answered ${response.status}.`);
  }
  return (await response.json()) as T;
}

export const api = {
  overview: () => get<Overview>("/overview"),
  stats: () => get<StatDef[]>("/stats"),
  leaderboard: (stat: string, scope: Scope, offset: number, limit: number) =>
    get<LeaderboardPage>(`/leaderboards/${encodeURIComponent(stat)}`, { scope, offset, limit }),
  searchPlayers: (q: string, signal?: AbortSignal) => get<PlayerSummary[]>("/players", { q, limit: 8 }, signal),
  player: (id: number) => get<PlayerProfile>(`/players/${id}`),
  similar: (id: number, samePosition: boolean, limit = 8) =>
    get<SimilarPlayer[]>(`/players/${id}/similar`, { samePosition, limit }),
  scoutMap: () => get<ScoutMap>("/scout/map"),
  teams: () => get<Team[]>("/teams"),
  ratings: () => get<TeamRating[]>("/teams/ratings"),
  fixtures: (gameweek: number) => get<FixtureView[]>("/fixtures", { gameweek }),
  predict: (homeId: number, awayId: number) => get<Prediction>("/predict", { homeId, awayId }),
  model: () => get<ModelReport>("/model"),
};
