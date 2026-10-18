package dev.matchiq.api;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/** The JSON shapes the API returns. Field names are the contract with the frontend (see docs/api.md). */
public final class Dtos {

    private Dtos() {
    }

    public record PlayerSummary(int id, String name, String fullName, int teamId, String teamName, String teamShort,
                                String position, int minutes, String style) {
    }

    public record StatDef(String key, String label, String description) {
    }

    public record LeaderboardEntry(int rank, PlayerSummary player, double per90, double raw) {
    }

    public record LeaderboardPage(String statKey, String label, String scope, long total, int offset, int limit,
                                  List<LeaderboardEntry> entries) {
    }

    /** One stat for one player. The rank is among players in the same position; null if it could not be found. */
    public record StatLine(String key, String label, String description, double raw, double per90, double percentile,
                           Integer positionRank, Long positionTotal) {
    }

    public record PlayerProfile(PlayerSummary player, List<StatLine> stats) {
    }

    public record SimilarPlayer(PlayerSummary player, double similarity) {
    }

    public record MapPoint(int id, String name, String teamShort, String position, String style, double x, double y) {
    }

    public record ScoutMap(List<String> styles, List<MapPoint> points) {
    }

    public record TeamRef(int id, String shortName, String displayName) {
    }

    public record Team(int id, String name, String displayName, String shortName, double elo, Integer eloRank,
                       boolean inLeague) {
    }

    public record EloPoint(LocalDate date, double elo) {
    }

    public record TeamRating(int id, String name, String displayName, String shortName, double elo, Integer eloRank,
                             boolean inLeague, List<EloPoint> history) {
    }

    public record FixtureView(int id, int gameweek, OffsetDateTime kickoff, String status, Integer homeGoals,
                              Integer awayGoals, TeamRef home, TeamRef away, double pHome, double pDraw, double pAway,
                              String predicted, String result) {
    }

    public record TeamSide(int id, String shortName, String displayName, double elo) {
    }

    public record Prediction(TeamSide home, TeamSide away, double pHome, double pDraw, double pAway, String predicted,
                             double homeAdvantage, double eloDiff, String model) {
    }

    public record Counts(int players, int teams, int fixtures, int upcoming) {
    }

    public record Headline(String chosenModel, double modelAccuracy, double baselineAccuracy, int testMatches) {
    }

    public record Overview(Map<String, Object> meta, Counts counts, Integer nextGameweek, Headline headline) {
    }

    public record ModelMetric(String model, double accuracy, double logLoss, boolean chosen) {
    }

    public record SeasonMetric(String season, int matches, double modelAccuracy, double homeAccuracy) {
    }

    public record ModelReport(String chosenModel, List<ModelMetric> metrics, List<SeasonMetric> seasons,
                              Map<String, Object> meta) {
    }
}
