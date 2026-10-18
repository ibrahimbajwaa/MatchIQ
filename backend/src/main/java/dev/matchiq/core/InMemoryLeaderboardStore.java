package dev.matchiq.core;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalDouble;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Leaderboards held in memory. It is the reference implementation the Redis and SQL versions are tested against, and
 * it makes the ranking rules runnable in plain unit tests.
 *
 * <p>Each board is an immutable snapshot: ids and scores in rank order, plus an id lookup. {@link #replace} builds the
 * new snapshot off to the side and publishes it with a single map write, so readers never block and never see a
 * half-built board. Rank queries are binary searches, O(log n).
 */
public final class InMemoryLeaderboardStore implements LeaderboardReader, LeaderboardWriter {

    private record Board(int[] ids, double[] scores, Map<Integer, Double> byId) {

        static final Board EMPTY = new Board(new int[0], new double[0], Map.of());

        /** Number of scores strictly greater than x. {@code scores} is sorted high to low. */
        int countGreater(double x) {
            int lo = 0;
            int hi = scores.length;
            while (lo < hi) {
                int mid = (lo + hi) >>> 1;
                if (scores[mid] > x) {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            return lo;
        }
    }

    private final Map<BoardKey, Board> boards = new ConcurrentHashMap<>();

    @Override
    public void replace(BoardKey key, Map<Integer, Double> scores) {
        List<Map.Entry<Integer, Double>> entries = new ArrayList<>(scores.entrySet());
        // High score first; among equal scores the higher id first (see LeaderboardReader).
        entries.sort(Map.Entry.<Integer, Double>comparingByValue().reversed()
                .thenComparing(Map.Entry.<Integer, Double>comparingByKey().reversed()));
        int[] ids = new int[entries.size()];
        double[] values = new double[entries.size()];
        for (int i = 0; i < ids.length; i++) {
            ids[i] = entries.get(i).getKey();
            values[i] = entries.get(i).getValue();
        }
        boards.put(key, new Board(ids, values, new HashMap<>(scores)));
    }

    @Override
    public List<ScoredId> top(BoardKey key, int offset, int limit) {
        if (offset < 0 || limit < 0) {
            throw new IllegalArgumentException("offset and limit must not be negative");
        }
        Board b = boards.getOrDefault(key, Board.EMPTY);
        int from = Math.min(offset, b.ids.length);
        int to = (int) Math.min((long) from + limit, b.ids.length);
        List<ScoredId> out = new ArrayList<>(to - from);
        for (int i = from; i < to; i++) {
            out.add(new ScoredId(b.ids[i], b.scores[i]));
        }
        return out;
    }

    @Override
    public long size(BoardKey key) {
        return boards.getOrDefault(key, Board.EMPTY).ids.length;
    }

    @Override
    public OptionalDouble scoreOf(BoardKey key, int playerId) {
        Double s = boards.getOrDefault(key, Board.EMPTY).byId.get(playerId);
        return s == null ? OptionalDouble.empty() : OptionalDouble.of(s);
    }

    @Override
    public long countGreater(BoardKey key, double score) {
        return boards.getOrDefault(key, Board.EMPTY).countGreater(score);
    }

    @Override
    public String toString() {
        return "InMemoryLeaderboardStore" + Arrays.toString(boards.keySet().toArray());
    }
}
