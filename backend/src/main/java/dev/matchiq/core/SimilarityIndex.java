package dev.matchiq.core;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.PriorityQueue;

/**
 * Finds the players whose statistical profile is closest to a given player's.
 *
 * <p>Each player is a vector of standardised per-90 stats (z-scores). Vectors are scaled to length 1 once, when the
 * index is built, so the cosine similarity of two players is just a dot product. That compares the <em>shape</em> of a
 * profile (what a player does) rather than its size.
 *
 * <p>A query scans every player once and keeps the best {@code k} in a bounded min-heap, so it costs O(n log k) time and
 * O(k) extra memory instead of sorting all n scores. The index is immutable, so any number of request threads can share
 * it without locking.
 */
public final class SimilarityIndex {

    /** A player's input to the index. */
    public record Vector(int id, String position, double[] zscores) {
    }

    /** Another player and how similar they are (1 = identical profile, -1 = opposite). */
    public record Neighbor(int id, double similarity) {
    }

    private final int[] ids;
    private final String[] positions;
    private final double[][] unit;
    private final Map<Integer, Integer> rowById;

    private SimilarityIndex(int[] ids, String[] positions, double[][] unit) {
        this.ids = ids;
        this.positions = positions;
        this.unit = unit;
        this.rowById = new HashMap<>();
        for (int row = 0; row < ids.length; row++) {
            rowById.put(ids[row], row);
        }
    }

    public static SimilarityIndex build(List<Vector> players) {
        int n = players.size();
        int[] ids = new int[n];
        String[] positions = new String[n];
        double[][] unit = new double[n][];
        int dims = n == 0 ? 0 : players.get(0).zscores().length;
        for (int row = 0; row < n; row++) {
            Vector v = players.get(row);
            if (v.zscores().length != dims) {
                throw new IllegalArgumentException("player " + v.id() + " has " + v.zscores().length
                        + " stats, expected " + dims);
            }
            ids[row] = v.id();
            positions[row] = v.position();
            double norm = 0;
            for (double z : v.zscores()) {
                norm += z * z;
            }
            norm = Math.sqrt(norm);
            double[] u = new double[dims];
            for (int d = 0; d < dims; d++) {
                u[d] = norm == 0 ? 0 : v.zscores()[d] / norm;   // an all-average player has no direction
            }
            unit[row] = u;
        }
        return new SimilarityIndex(ids, positions, unit);
    }

    public int size() {
        return ids.length;
    }

    public boolean contains(int playerId) {
        return rowById.containsKey(playerId);
    }

    /**
     * The {@code k} players most similar to {@code playerId}, best first. Ties are ordered by player id so results
     * are deterministic.
     *
     * @throws NoSuchElementException if the player is not in the index
     */
    public List<Neighbor> mostSimilar(int playerId, int k, boolean samePositionOnly) {
        if (k < 1) {
            throw new IllegalArgumentException("k must be at least 1");
        }
        Integer queryRow = rowById.get(playerId);
        if (queryRow == null) {
            throw new NoSuchElementException("unknown player " + playerId);
        }
        double[] q = unit[queryRow];
        String position = positions[queryRow];

        // Min-heap ordered worst-first, so the head is always the neighbour to throw out next.
        Comparator<Neighbor> bestFirst = Comparator.comparingDouble(Neighbor::similarity).reversed()
                .thenComparingInt(Neighbor::id);
        PriorityQueue<Neighbor> heap = new PriorityQueue<>(k + 1, bestFirst.reversed());

        for (int row = 0; row < ids.length; row++) {
            if (row == queryRow || (samePositionOnly && !positions[row].equals(position))) {
                continue;
            }
            double dot = 0;
            double[] u = unit[row];
            for (int d = 0; d < q.length; d++) {
                dot += q[d] * u[d];
            }
            Neighbor candidate = new Neighbor(ids[row], dot);
            if (heap.size() < k) {
                heap.add(candidate);
            } else if (bestFirst.compare(candidate, heap.peek()) < 0) {
                heap.poll();
                heap.add(candidate);
            }
        }
        List<Neighbor> out = new ArrayList<>(heap);
        out.sort(bestFirst);
        return out;
    }
}
