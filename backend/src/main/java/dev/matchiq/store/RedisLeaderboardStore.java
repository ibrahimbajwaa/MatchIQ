package dev.matchiq.store;

import dev.matchiq.core.BoardKey;
import dev.matchiq.core.LeaderboardReader;
import dev.matchiq.core.LeaderboardWriter;
import dev.matchiq.core.ScoredId;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.OptionalDouble;
import java.util.Set;
import java.util.UUID;
import org.springframework.data.redis.core.DefaultTypedTuple;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.data.redis.core.ZSetOperations.TypedTuple;
import org.springframework.stereotype.Component;

/**
 * Leaderboards in Redis sorted sets, one per board, at {@code lb:v1:<stat>:<scope>}.
 *
 * <ul>
 *   <li><b>Members</b> are player ids, zero-padded to six digits. Redis orders equal scores by member, so
 *       {@code ZREVRANGE} puts the higher id first, which is the tie rule every {@link LeaderboardReader} follows.</li>
 *   <li><b>Strictly greater</b> counts use {@code ZCOUNT key nextUp(score) +inf}. {@code Math.nextUp} is the smallest
 *       double above the score, and Redis parses the decimal text Java prints back to exactly that double.</li>
 *   <li><b>Replacing a board</b> builds a temporary set and {@code RENAME}s it over the live key. RENAME is atomic, so
 *       a request sees the old board or the new one, never a half-written one.</li>
 * </ul>
 */
@Component
public class RedisLeaderboardStore implements LeaderboardReader, LeaderboardWriter {

    private final StringRedisTemplate redis;

    public RedisLeaderboardStore(StringRedisTemplate redis) {
        this.redis = redis;
    }

    static String key(BoardKey board) {
        return "lb:v1:" + board.stat() + ":" + board.scope();
    }

    static String member(int playerId) {
        return String.format("%06d", playerId);
    }

    @Override
    public void replace(BoardKey board, Map<Integer, Double> scores) {
        String live = key(board);
        if (scores.isEmpty()) {
            redis.delete(live);
            return;
        }
        String building = live + ":building:" + UUID.randomUUID();
        Set<TypedTuple<String>> tuples = new LinkedHashSet<>();
        scores.forEach((id, score) -> tuples.add(new DefaultTypedTuple<>(member(id), score)));
        try {
            redis.opsForZSet().add(building, tuples);
            redis.rename(building, live);
        } finally {
            redis.delete(building);   // nothing left to delete after a successful rename; cleans up after a failure
        }
    }

    @Override
    public List<ScoredId> top(BoardKey board, int offset, int limit) {
        if (limit == 0) {
            return List.of();          // ZREVRANGE with end = start - 1 would mean "to the end" for offset 0
        }
        Set<TypedTuple<String>> rows = redis.opsForZSet()
                .reverseRangeWithScores(key(board), offset, (long) offset + limit - 1);
        List<ScoredId> out = new ArrayList<>();
        if (rows != null) {
            for (TypedTuple<String> row : rows) {
                out.add(new ScoredId(Integer.parseInt(row.getValue()), row.getScore()));
            }
        }
        return out;
    }

    @Override
    public long size(BoardKey board) {
        Long n = redis.opsForZSet().size(key(board));
        return n == null ? 0 : n;
    }

    @Override
    public OptionalDouble scoreOf(BoardKey board, int playerId) {
        Double s = redis.opsForZSet().score(key(board), member(playerId));
        return s == null ? OptionalDouble.empty() : OptionalDouble.of(s);
    }

    @Override
    public long countGreater(BoardKey board, double score) {
        Long n = redis.opsForZSet().count(key(board), Math.nextUp(score), Double.POSITIVE_INFINITY);
        return n == null ? 0 : n;
    }
}
