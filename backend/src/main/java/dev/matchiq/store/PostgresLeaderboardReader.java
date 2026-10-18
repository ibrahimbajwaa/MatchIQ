package dev.matchiq.store;

import dev.matchiq.core.BoardKey;
import dev.matchiq.core.LeaderboardReader;
import dev.matchiq.core.ScoredId;
import java.util.List;
import java.util.Optional;
import java.util.OptionalDouble;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/**
 * Leaderboards computed straight from Postgres. Slower than Redis but always correct, so it is both the source the
 * Redis boards are built from and the fallback when Redis is unavailable. The queries order by score and then player
 * id, both descending, to match Redis.
 */
@Component
public class PostgresLeaderboardReader implements LeaderboardReader {

    private final JdbcClient jdbc;

    public PostgresLeaderboardReader(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<ScoredId> top(BoardKey board, int offset, int limit) {
        return jdbc.sql(Sql.get("board_top"))
                .param("stat", board.stat())
                .param("scope", board.scope())
                .param("limit", limit)
                .param("offset", offset)
                .query((rs, n) -> new ScoredId(rs.getInt("id"), rs.getDouble("score")))
                .list();
    }

    @Override
    public long size(BoardKey board) {
        return jdbc.sql(Sql.get("board_size"))
                .param("stat", board.stat())
                .param("scope", board.scope())
                .query(Long.class)
                .single();
    }

    @Override
    public OptionalDouble scoreOf(BoardKey board, int playerId) {
        Optional<Double> score = jdbc.sql(Sql.get("board_score"))
                .param("stat", board.stat())
                .param("scope", board.scope())
                .param("id", playerId)
                .query(Double.class)
                .optional();
        return score.map(OptionalDouble::of).orElseGet(OptionalDouble::empty);
    }

    @Override
    public long countGreater(BoardKey board, double score) {
        return jdbc.sql(Sql.get("board_count_greater"))
                .param("stat", board.stat())
                .param("scope", board.scope())
                .param("score", score)
                .query(Long.class)
                .single();
    }
}
