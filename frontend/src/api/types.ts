// Mirrors backend/src/main/java/dev/matchiq/api/Dtos.java. `npm run check:contract` fails if the mock API (and so
// these shapes) ever drifts from the Java records.

export type Position = "Defender" | "Midfielder" | "Forward";
export type Scope = "all" | Position;
export type OutcomeCode = "H" | "D" | "A";

export interface PlayerSummary {
  id: number;
  name: string;
  fullName: string;
  teamId: number;
  teamName: string;
  teamShort: string;
  position: Position;
  minutes: number;
  style: string | null;
}

export interface StatDef {
  key: string;
  label: string;
  description: string;
}

export interface LeaderboardEntry {
  rank: number;
  player: PlayerSummary;
  per90: number;
  raw: number;
}

export interface LeaderboardPage {
  statKey: string;
  label: string;
  scope: string;
  total: number;
  offset: number;
  limit: number;
  entries: LeaderboardEntry[];
}

export interface StatLine {
  key: string;
  label: string;
  description: string;
  raw: number;
  per90: number;
  percentile: number;
  positionRank: number | null;
  positionTotal: number | null;
}

export interface PlayerProfile {
  player: PlayerSummary;
  stats: StatLine[];
}

export interface SimilarPlayer {
  player: PlayerSummary;
  similarity: number;
}

export interface MapPoint {
  id: number;
  name: string;
  teamShort: string;
  position: Position;
  style: string | null;
  x: number;
  y: number;
}

export interface ScoutMap {
  styles: string[];
  points: MapPoint[];
}

export interface TeamRef {
  id: number;
  shortName: string;
  displayName: string;
}

export interface Team {
  id: number;
  name: string;
  displayName: string;
  shortName: string;
  elo: number;
  eloRank: number | null;
  inLeague: boolean;
}

export interface EloPoint {
  date: string;
  elo: number;
}

export interface TeamRating extends Team {
  history: EloPoint[];
}

export interface FixtureView {
  id: number;
  gameweek: number;
  kickoff: string;
  status: string;
  homeGoals: number | null;
  awayGoals: number | null;
  home: TeamRef;
  away: TeamRef;
  pHome: number;
  pDraw: number;
  pAway: number;
  predicted: OutcomeCode;
  result: OutcomeCode | null;
}

export interface TeamSide {
  id: number;
  shortName: string;
  displayName: string;
  elo: number;
}

export interface Prediction {
  home: TeamSide;
  away: TeamSide;
  pHome: number;
  pDraw: number;
  pAway: number;
  predicted: OutcomeCode;
  homeAdvantage: number;
  eloDiff: number;
  model: string;
}

export interface Overview {
  meta: Record<string, unknown>;
  counts: { players: number; teams: number; fixtures: number; upcoming: number };
  nextGameweek: number | null;
  headline: { chosenModel: string; modelAccuracy: number; baselineAccuracy: number; testMatches: number };
}

export interface ModelMetric {
  model: string;
  accuracy: number;
  logLoss: number;
  chosen: boolean;
}

export interface SeasonMetric {
  season: string;
  matches: number;
  modelAccuracy: number;
  homeAccuracy: number;
}

export interface ModelReport {
  chosenModel: string;
  metrics: ModelMetric[];
  seasons: SeasonMetric[];
  meta: Record<string, unknown>;
}

/** RFC 7807 problem details, as the backend returns them for every error. */
export interface Problem {
  title?: string;
  status?: number;
  detail?: string;
}
