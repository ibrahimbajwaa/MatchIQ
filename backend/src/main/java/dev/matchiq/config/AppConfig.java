package dev.matchiq.config;

import dev.matchiq.core.FailoverLeaderboardReader;
import dev.matchiq.core.LeaderboardReader;
import dev.matchiq.core.Leaderboards;
import dev.matchiq.core.MatchModel;
import dev.matchiq.core.SimilarityIndex;
import dev.matchiq.store.BoardState;
import dev.matchiq.store.PlayerRepository;
import dev.matchiq.store.PostgresLeaderboardReader;
import dev.matchiq.store.RedisLeaderboardStore;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.io.IOException;
import java.io.InputStream;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.io.ClassPathResource;

/** Wires the framework-free classes in {@code dev.matchiq.core} into the application. */
@Configuration
public class AppConfig {

    @Bean
    MatchModel matchModel() throws IOException {
        try (InputStream in = new ClassPathResource("model/elo_logit.properties").getInputStream()) {
            return MatchModel.load(in);
        }
    }

    /** Built once from Postgres at startup; it is immutable, so request threads share it without locking. */
    @Bean
    SimilarityIndex similarityIndex(PlayerRepository players) {
        return SimilarityIndex.build(players.similarityVectors());
    }

    /** What the application reads leaderboards from: Redis, falling back to Postgres. */
    @Bean
    @Primary
    LeaderboardReader leaderboardReader(RedisLeaderboardStore redis, PostgresLeaderboardReader postgres,
                                        BoardState state, MeterRegistry meters) {
        Counter fallbacks = Counter.builder("matchiq.leaderboard.fallback")
                .description("Leaderboard reads served from Postgres because Redis was unavailable or empty")
                .register(meters);
        return new FailoverLeaderboardReader(redis, postgres, () -> {
            fallbacks.increment();
            state.markLost();
        });
    }

    @Bean
    Leaderboards leaderboards(LeaderboardReader reader) {
        return new Leaderboards(reader);
    }
}
