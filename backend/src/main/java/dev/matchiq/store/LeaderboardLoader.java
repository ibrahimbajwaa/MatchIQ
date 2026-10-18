package dev.matchiq.store;

import dev.matchiq.core.BoardKey;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.SmartInitializingSingleton;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Builds the Redis leaderboards from Postgres: once at startup, before the web server accepts requests, and again
 * every 30 seconds while Redis is missing or empty. If Redis is down at startup the application still starts and
 * serves leaderboards from Postgres, then switches back as soon as Redis returns.
 */
@Component
public class LeaderboardLoader implements SmartInitializingSingleton {

    private static final Logger log = LoggerFactory.getLogger(LeaderboardLoader.class);

    private final PlayerRepository players;
    private final RedisLeaderboardStore redis;
    private final BoardState state;

    public LeaderboardLoader(PlayerRepository players, RedisLeaderboardStore redis, BoardState state) {
        this.players = players;
        this.redis = redis;
        this.state = state;
    }

    @Override
    public void afterSingletonsInstantiated() {
        fill();
    }

    @Scheduled(fixedDelayString = "${matchiq.leaderboards.refill-ms:30000}",
            initialDelayString = "${matchiq.leaderboards.refill-ms:30000}")
    public void refillIfNeeded() {
        if (!state.redisReady()) {
            fill();
        }
    }

    private synchronized void fill() {
        try {
            Map<BoardKey, Map<Integer, Double>> boards = players.allBoards();
            boards.forEach(redis::replace);
            state.markReady();
            log.info("Loaded {} leaderboards into Redis", boards.size());
        } catch (RuntimeException e) {
            state.markLost();
            log.warn("Could not load leaderboards into Redis ({}); serving them from Postgres until it is back", e.toString());
        }
    }
}
