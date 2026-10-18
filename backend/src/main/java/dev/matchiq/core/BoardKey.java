package dev.matchiq.core;

/**
 * Identifies one leaderboard: a stat (such as {@code expected_goals}) ranked within a scope, which is either
 * {@link #ALL} players or a single position ({@code Defender}, {@code Midfielder}, {@code Forward}).
 */
public record BoardKey(String stat, String scope) {

    public static final String ALL = "all";

    public BoardKey {
        if (stat == null || stat.isBlank() || scope == null || scope.isBlank()) {
            throw new IllegalArgumentException("a board needs a stat and a scope");
        }
    }

    public static BoardKey all(String stat) {
        return new BoardKey(stat, ALL);
    }

    public boolean isAll() {
        return ALL.equals(scope);
    }
}
