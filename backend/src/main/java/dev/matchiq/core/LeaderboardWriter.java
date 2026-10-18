package dev.matchiq.core;

import java.util.Map;

/** Write side of a leaderboard store. */
public interface LeaderboardWriter {

    /**
     * Replaces a whole board. Readers must see either the old board or the new one, never a mixture of the two.
     *
     * @param scores player id to score
     */
    void replace(BoardKey board, Map<Integer, Double> scores);
}
