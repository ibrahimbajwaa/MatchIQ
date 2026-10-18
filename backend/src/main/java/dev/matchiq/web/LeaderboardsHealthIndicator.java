package dev.matchiq.web;

import dev.matchiq.store.BoardState;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

/** Shows where leaderboards are being served from. Always UP: falling back to Postgres is slower, not broken. */
@Component
public class LeaderboardsHealthIndicator implements HealthIndicator {

    private final BoardState state;

    public LeaderboardsHealthIndicator(BoardState state) {
        this.state = state;
    }

    @Override
    public Health health() {
        return Health.up().withDetail("source", state.redisReady() ? "redis" : "postgres-fallback").build();
    }
}
