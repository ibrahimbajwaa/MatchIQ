package dev.matchiq.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import java.util.OptionalDouble;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class FailoverLeaderboardReaderTest {

    private static final BoardKey B = BoardKey.all("goals");

    /** A reader that always fails, like a Redis server that has gone away. */
    private static final LeaderboardReader DOWN = new LeaderboardReader() {
        private RuntimeException boom() {
            return new IllegalStateException("redis is down");
        }

        public List<ScoredId> top(BoardKey b, int o, int l) {
            throw boom();
        }

        public long size(BoardKey b) {
            throw boom();
        }

        public OptionalDouble scoreOf(BoardKey b, int id) {
            throw boom();
        }

        public long countGreater(BoardKey b, double s) {
            throw boom();
        }
    };

    private static InMemoryLeaderboardStore storeWith(Map<Integer, Double> scores) {
        InMemoryLeaderboardStore s = new InMemoryLeaderboardStore();
        s.replace(B, scores);
        return s;
    }

    @Test
    void healthyPrimaryAnswersAndTheFallbackIsNeverTouched() {
        AtomicInteger fallbacks = new AtomicInteger();
        var primary = storeWith(Map.of(1, 9.0, 2, 8.0));
        var fallback = storeWith(Map.of(7, 1.0));
        var reader = new FailoverLeaderboardReader(primary, fallback, fallbacks::incrementAndGet);
        assertEquals(List.of(1, 2), reader.top(B, 0, 10).stream().map(ScoredId::id).toList());
        assertEquals(2, reader.size(B));
        assertEquals(9.0, reader.scoreOf(B, 1).getAsDouble(), 0.0);
        assertEquals(1, reader.countGreater(B, 8.0));
        assertEquals(0, fallbacks.get());
    }

    @Test
    void aDownPrimaryIsServedFromTheFallbackAndCounted() {
        AtomicInteger fallbacks = new AtomicInteger();
        var fallback = storeWith(Map.of(7, 1.0, 8, 2.0));
        var reader = new FailoverLeaderboardReader(DOWN, fallback, fallbacks::incrementAndGet);
        assertEquals(List.of(8, 7), reader.top(B, 0, 10).stream().map(ScoredId::id).toList());
        assertEquals(2, reader.size(B));
        assertEquals(2.0, reader.scoreOf(B, 8).getAsDouble(), 0.0);
        assertEquals(1, reader.countGreater(B, 1.0));
        assertEquals(4, fallbacks.get());
    }

    @Test
    void aPrimaryThatLostItsDataIsTreatedLikeADownPrimary() {
        AtomicInteger fallbacks = new AtomicInteger();
        var emptyPrimary = new InMemoryLeaderboardStore();        // e.g. Redis restarted without persistence
        var fallback = storeWith(Map.of(7, 1.0));
        var reader = new FailoverLeaderboardReader(emptyPrimary, fallback, fallbacks::incrementAndGet);
        assertEquals(1, reader.top(B, 0, 10).size());
        assertEquals(1, reader.size(B));
        assertTrue(reader.scoreOf(B, 7).isPresent());
        assertEquals(3, fallbacks.get());
    }
}
