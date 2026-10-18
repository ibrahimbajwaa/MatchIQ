package dev.matchiq.core;

import java.util.List;
import java.util.OptionalDouble;
import java.util.function.Supplier;

/**
 * Reads from a fast primary store (Redis) and quietly falls back to a slower source of truth (Postgres) when the
 * primary is down or has lost its data. The site gets slower, not broken.
 *
 * <p>The primary is asked first and costs one call on the happy path. The fallback is used when the primary throws, or
 * when it answers "nothing here", which is what a Redis server that was restarted without persistence says for every
 * board. {@code onFallback} lets the caller count these events for a metric.
 */
public final class FailoverLeaderboardReader implements LeaderboardReader {

    private final LeaderboardReader primary;
    private final LeaderboardReader fallback;
    private final Runnable onFallback;

    public FailoverLeaderboardReader(LeaderboardReader primary, LeaderboardReader fallback, Runnable onFallback) {
        this.primary = primary;
        this.fallback = fallback;
        this.onFallback = onFallback;
    }

    @Override
    public List<ScoredId> top(BoardKey board, int offset, int limit) {
        return withFallback(() -> primary.top(board, offset, limit), List::isEmpty,
                () -> fallback.top(board, offset, limit));
    }

    @Override
    public long size(BoardKey board) {
        return withFallback(() -> primary.size(board), size -> size == 0, () -> fallback.size(board));
    }

    @Override
    public OptionalDouble scoreOf(BoardKey board, int playerId) {
        return withFallback(() -> primary.scoreOf(board, playerId), OptionalDouble::isEmpty,
                () -> fallback.scoreOf(board, playerId));
    }

    @Override
    public long countGreater(BoardKey board, double score) {
        // Only called after scoreOf or top found the board, so an empty answer here is a real zero.
        return withFallback(() -> primary.countGreater(board, score), count -> false,
                () -> fallback.countGreater(board, score));
    }

    private <T> T withFallback(Supplier<T> fromPrimary, java.util.function.Predicate<T> looksLost,
                               Supplier<T> fromFallback) {
        try {
            T answer = fromPrimary.get();
            if (!looksLost.test(answer)) {
                return answer;
            }
        } catch (RuntimeException primaryDown) {
            // fall through to the source of truth
        }
        onFallback.run();
        return fromFallback.get();
    }
}
