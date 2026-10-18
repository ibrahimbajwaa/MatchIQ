package dev.matchiq.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.matchiq.core.Leaderboards.Page;
import dev.matchiq.core.Leaderboards.RankedEntry;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;

class LeaderboardsTest {

    private static final BoardKey B = BoardKey.all("goals");

    private static Leaderboards withScores(Map<Integer, Double> scores) {
        InMemoryLeaderboardStore store = new InMemoryLeaderboardStore();
        store.replace(B, scores);
        return new Leaderboards(store);
    }

    @Test
    void matchesPythonsTopFifteenForEveryStatAndPosition() {
        InMemoryLeaderboardStore store = new InMemoryLeaderboardStore();
        List<GoldenFiles.GoldenPlayer> players = GoldenFiles.players();
        for (int s = 0; s < GoldenFiles.STATS.size(); s++) {
            for (String scope : List.of("all", "Defender", "Midfielder", "Forward")) {
                Map<Integer, Double> scores = new HashMap<>();
                for (GoldenFiles.GoldenPlayer p : players) {
                    if (scope.equals("all") || scope.equals(p.position())) {
                        scores.put(p.id(), p.per90()[s]);
                    }
                }
                store.replace(new BoardKey(GoldenFiles.STATS.get(s), scope), scores);
            }
        }
        Leaderboards boards = new Leaderboards(store);

        Map<String, List<Map<String, String>>> byBoard = new LinkedHashMap<>();
        for (Map<String, String> row : GoldenFiles.read("leaderboards.csv")) {
            byBoard.computeIfAbsent(row.get("stat") + "/" + row.get("scope"), k -> new java.util.ArrayList<>()).add(row);
        }
        assertEquals(36, byBoard.size());
        for (Map.Entry<String, List<Map<String, String>>> b : byBoard.entrySet()) {
            String[] parts = b.getKey().split("/");
            Page page = boards.page(new BoardKey(parts[0], parts[1]), 0, 15);
            assertEquals(15, page.entries().size(), b.getKey());
            for (int i = 0; i < 15; i++) {
                Map<String, String> want = b.getValue().get(i);
                RankedEntry got = page.entries().get(i);
                assertEquals(Integer.parseInt(want.get("playerId")), got.playerId(), b.getKey() + " position " + (i + 1));
                assertEquals(Integer.parseInt(want.get("rank")), got.rank(), b.getKey() + " rank at " + (i + 1));
                assertEquals(Double.parseDouble(want.get("score")), got.score(), 0.0, b.getKey());
            }
        }
    }

    @Test
    void tiedPlayersShareARankAndTheNextRankSkipsAhead() {
        Leaderboards lb = withScores(Map.of(1, 5.0, 2, 3.0, 3, 3.0, 4, 3.0, 5, 1.0));
        List<RankedEntry> got = lb.page(B, 0, 10).entries();
        assertEquals(List.of(1, 2, 2, 2, 5), got.stream().map(RankedEntry::rank).toList());
        // equal scores: higher id first
        assertEquals(List.of(1, 4, 3, 2, 5), got.stream().map(RankedEntry::playerId).toList());
    }

    @Test
    void aTieThatStraddlesAPageBoundaryKeepsItsRank() {
        Leaderboards lb = withScores(Map.of(1, 5.0, 2, 3.0, 3, 3.0, 4, 3.0, 5, 1.0));
        // second page starts in the middle of the three-way tie for rank 2
        List<RankedEntry> page2 = lb.page(B, 2, 2).entries();
        assertEquals(List.of(3, 2), page2.stream().map(RankedEntry::playerId).toList());
        assertEquals(List.of(2, 2), page2.stream().map(RankedEntry::rank).toList());
        List<RankedEntry> page3 = lb.page(B, 4, 2).entries();
        assertEquals(1, page3.size());
        assertEquals(5, page3.get(0).rank());
    }

    @Test
    void rankOfReportsRankSizeAndScoreOrEmptyForAnUnknownPlayer() {
        Leaderboards lb = withScores(Map.of(1, 5.0, 2, 3.0, 3, 3.0, 4, 1.0));
        var rank = lb.rankOf(B, 3).orElseThrow();
        assertEquals(2, rank.rank());
        assertEquals(4, rank.outOf());
        assertEquals(3.0, rank.score(), 0.0);
        assertEquals(1, lb.rankOf(B, 1).orElseThrow().rank());
        assertEquals(4, lb.rankOf(B, 4).orElseThrow().rank());
        assertTrue(lb.rankOf(B, 99).isEmpty());
    }

    @Test
    void anUnknownOrEmptyBoardIsEmptyNotAnError() {
        Leaderboards lb = new Leaderboards(new InMemoryLeaderboardStore());
        Page page = lb.page(B, 0, 10);
        assertEquals(0, page.total());
        assertTrue(page.entries().isEmpty());
    }

    @Test
    void pagingPastTheEndReturnsNothing() {
        Leaderboards lb = withScores(Map.of(1, 2.0, 2, 1.0));
        assertTrue(lb.page(B, 5, 10).entries().isEmpty());
        assertEquals(2, lb.page(B, 5, 10).total());
    }

    @Test
    void negativeOffsetOrLimitIsRejected() {
        Leaderboards lb = withScores(Map.of(1, 2.0));
        assertThrows(IllegalArgumentException.class, () -> lb.page(B, -1, 10));
        assertThrows(IllegalArgumentException.class, () -> lb.page(B, 0, -1));
    }

    @Test
    void readersNeverSeeAHalfReplacedBoard() throws Exception {
        // Board A holds ids 0..99 all scoring 1.0; board B holds ids 1000..1099 all scoring 2.0.
        // A reader that ever sees a mixture of the two (or a partial board) would have caught a torn replace.
        Map<Integer, Double> a = new HashMap<>();
        Map<Integer, Double> b = new HashMap<>();
        for (int i = 0; i < 100; i++) {
            a.put(i, 1.0);
            b.put(1000 + i, 2.0);
        }
        InMemoryLeaderboardStore store = new InMemoryLeaderboardStore();
        store.replace(B, a);
        AtomicBoolean stop = new AtomicBoolean();
        ExecutorService pool = Executors.newFixedThreadPool(5);
        Future<?> writer = pool.submit(() -> {
            for (int i = 0; !stop.get(); i++) {
                store.replace(B, i % 2 == 0 ? b : a);
            }
        });
        List<Future<Integer>> readers = new java.util.ArrayList<>();
        for (int t = 0; t < 4; t++) {
            readers.add(pool.submit(() -> {
                int torn = 0;
                for (int i = 0; i < 20_000; i++) {
                    List<ScoredId> top = store.top(B, 0, 1000);
                    boolean fromA = top.get(0).id() < 1000;
                    boolean consistent = top.size() == 100
                            && top.stream().allMatch(e -> (e.id() < 1000) == fromA && e.score() == (fromA ? 1.0 : 2.0));
                    if (!consistent) {
                        torn++;
                    }
                }
                return torn;
            }));
        }
        int torn = 0;
        for (Future<Integer> r : readers) {
            torn += r.get(60, TimeUnit.SECONDS);
        }
        stop.set(true);
        writer.get(10, TimeUnit.SECONDS);
        pool.shutdownNow();
        assertEquals(0, torn, "a reader saw a board that was neither the old one nor the new one");
        assertFalse(store.top(B, 0, 1).isEmpty());
    }
}
