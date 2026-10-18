package dev.matchiq.core;

import java.util.List;
import java.util.OptionalDouble;

/**
 * Read side of a leaderboard store.
 *
 * <p>Every implementation must order entries the same way: highest score first, and among equal scores the higher
 * player id first. That is the order Redis returns for a sorted set whose members are zero-padded ids, and the order
 * the SQL fallback asks for, so a request gets the same answer from either source.
 */
public interface LeaderboardReader {

    /** Entries in rank order, starting at {@code offset} (0-based) and at most {@code limit} long. */
    List<ScoredId> top(BoardKey board, int offset, int limit);

    /** Number of entries on the board. */
    long size(BoardKey board);

    /** The player's score, or empty if they are not on the board. */
    OptionalDouble scoreOf(BoardKey board, int playerId);

    /** How many entries have a score strictly higher than {@code score}. */
    long countGreater(BoardKey board, double score);
}
