package dev.matchiq.store;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.stereotype.Component;

/** Whether the Redis leaderboards are loaded and trusted. Reads fall back to Postgres while this is false. */
@Component
public final class BoardState {

    private final AtomicBoolean redisReady = new AtomicBoolean(false);

    public BoardState(MeterRegistry meters) {
        Gauge.builder("matchiq.leaderboards.redis.ready", this, s -> s.redisReady() ? 1 : 0)
                .description("1 when leaderboards are served from Redis, 0 when they come from the Postgres fallback")
                .register(meters);
    }

    public boolean redisReady() {
        return redisReady.get();
    }

    public void markReady() {
        redisReady.set(true);
    }

    /** Called when a Redis read failed or came back empty, so the loader rebuilds the boards on its next pass. */
    public void markLost() {
        redisReady.set(false);
    }
}
