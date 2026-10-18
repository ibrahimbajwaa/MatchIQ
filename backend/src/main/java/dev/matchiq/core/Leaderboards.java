package dev.matchiq.core;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.OptionalDouble;

/**
 * Turns raw leaderboard reads into ranked answers.
 *
 * <p>Ranking is "competition" style: players on equal scores share a rank and the next rank skips ahead (1, 2, 2, 4).
 * A player's rank is 1 + the number of players with a strictly higher score.
 */
public final class Leaderboards {

    public record RankedEntry(int rank, int playerId, double score) {
    }

    public record Page(long total, List<RankedEntry> entries) {
    }

    public record PlayerRank(int rank, long outOf, double score) {
    }

    private final LeaderboardReader reader;

    public Leaderboards(LeaderboardReader reader) {
        this.reader = reader;
    }

    public Page page(BoardKey board, int offset, int limit) {
        List<ScoredId> rows = reader.top(board, offset, limit);
        long total = reader.size(board);
        List<RankedEntry> out = new ArrayList<>(rows.size());
        int rank = 0;
        for (int i = 0; i < rows.size(); i++) {
            ScoredId row = rows.get(i);
            if (i == 0) {
                // Ties can straddle the page boundary, so the first rank is looked up, not assumed from the offset.
                rank = (int) (1 + reader.countGreater(board, row.score()));
            } else if (row.score() != rows.get(i - 1).score()) {
                rank = offset + i + 1;
            }
            out.add(new RankedEntry(rank, row.id(), row.score()));
        }
        return new Page(total, out);
    }

    public Optional<PlayerRank> rankOf(BoardKey board, int playerId) {
        OptionalDouble score = reader.scoreOf(board, playerId);
        if (score.isEmpty()) {
            return Optional.empty();
        }
        int rank = (int) (1 + reader.countGreater(board, score.getAsDouble()));
        return Optional.of(new PlayerRank(rank, reader.size(board), score.getAsDouble()));
    }
}
