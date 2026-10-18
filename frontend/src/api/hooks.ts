import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { Scope } from "./types";

// Football data changes at most a few times a day, so a minute of freshness is plenty.
const STALE = 60_000;

export const useOverview = () => useQuery({ queryKey: ["overview"], queryFn: api.overview, staleTime: STALE });
export const useStats = () => useQuery({ queryKey: ["stats"], queryFn: api.stats, staleTime: Infinity });

export const useLeaderboard = (stat: string, scope: Scope, offset: number, limit: number) =>
  useQuery({
    queryKey: ["leaderboard", stat, scope, offset, limit],
    queryFn: () => api.leaderboard(stat, scope, offset, limit),
    placeholderData: keepPreviousData,
    staleTime: STALE,
  });

export const usePlayerSearch = (q: string) =>
  useQuery({
    queryKey: ["search", q],
    queryFn: ({ signal }) => api.searchPlayers(q, signal),
    enabled: q.trim().length >= 2,
    staleTime: STALE,
    placeholderData: keepPreviousData,
  });

export const usePlayer = (id: number) =>
  useQuery({ queryKey: ["player", id], queryFn: () => api.player(id), staleTime: STALE, enabled: Number.isInteger(id) });

export const useSimilar = (id: number | null, samePosition: boolean, limit = 8) =>
  useQuery({
    queryKey: ["similar", id, samePosition, limit],
    queryFn: () => api.similar(id as number, samePosition, limit),
    enabled: id !== null,
    staleTime: STALE,
  });

export const useScoutMap = () => useQuery({ queryKey: ["scout-map"], queryFn: api.scoutMap, staleTime: STALE });
export const useTeams = () => useQuery({ queryKey: ["teams"], queryFn: api.teams, staleTime: STALE });
export const useRatings = () => useQuery({ queryKey: ["ratings"], queryFn: api.ratings, staleTime: STALE });
export const useFixtures = (gameweek: number) =>
  useQuery({ queryKey: ["fixtures", gameweek], queryFn: () => api.fixtures(gameweek), staleTime: STALE, placeholderData: keepPreviousData });

export const usePrediction = (homeId: number | null, awayId: number | null) =>
  useQuery({
    queryKey: ["predict", homeId, awayId],
    queryFn: () => api.predict(homeId as number, awayId as number),
    enabled: homeId !== null && awayId !== null && homeId !== awayId,
    staleTime: STALE,
  });

export const useModel = () => useQuery({ queryKey: ["model"], queryFn: api.model, staleTime: STALE });
